import csv
import io
import ipaddress
from flask import Blueprint, request, jsonify, Response
from database.connection import get_connection

advanced = Blueprint("advanced", __name__)

TIME_RANGES = {
    "1h": 3600,
    "24h": 86400,
    "7d": 604800,
    "30d": 2592000
}


def build_filters():
    conditions = []
    params = []

    selected = request.args.get("range", "all")

    if selected in TIME_RANGES:
        conditions.append(
            "created_at >= DATE_SUB(NOW(), INTERVAL %s SECOND)"
        )
        params.append(TIME_RANGES[selected])

    severity = request.args.get("severity", "All")
    status = request.args.get("status", "All")
    search = request.args.get("search", "").strip()

    if severity != "All":
        conditions.append("severity = %s")
        params.append(severity)

    if status != "All":
        conditions.append("status = %s")
        params.append(status)

    if search:
        conditions.append("""
            LOCATE(%s, LOWER(CONCAT_WS(' ',
                CAST(id AS CHAR),
                source_ip,
                destination_ip,
                signature
            ))) > 0
        """)
        params.append(search.lower())

    where = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    return where, params


@advanced.route("/api/advanced/alerts")
def advanced_alerts():
    where, params = build_filters()

    page = max(1, request.args.get("page", 1, type=int))
    limit = request.args.get("limit", 30, type=int)

    if limit not in (15, 30, 50, 100):
        limit = 30

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM alerts" + where,
            tuple(params)
        )

        total = cursor.fetchone()["total"]
        pages = max(1, (total + limit - 1) // limit)
        page = min(page, pages)

        cursor.execute(
            "SELECT * FROM alerts" + where +
            " ORDER BY id DESC LIMIT %s OFFSET %s",
            tuple(params + [limit, (page - 1) * limit])
        )

        alerts = cursor.fetchall()

        counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "Unknown": 0
        }

        cursor.execute(
            "SELECT severity, COUNT(*) AS total FROM alerts"
            + where + " GROUP BY severity",
            tuple(params)
        )

        for row in cursor.fetchall():
            counts[row["severity"]] = row["total"]

        status_counts = {
            "Open": 0,
            "Investigating": 0,
            "Resolved": 0
        }

        cursor.execute(
            "SELECT status, COUNT(*) AS total FROM alerts"
            + where + " GROUP BY status",
            tuple(params)
        )

        for row in cursor.fetchall():
            status_counts[row["status"]] = row["total"]

        cursor.execute("""
            SELECT COALESCE(NULLIF(category, ''),
                'Uncategorized') AS category,
                COUNT(*) AS total
            FROM alerts
        """ + where + """
            GROUP BY COALESCE(NULLIF(category, ''),
                'Uncategorized')
            ORDER BY total DESC
        """, tuple(params))

        categories = cursor.fetchall()

        cursor.execute("""
            SELECT source_ip, COUNT(*) AS total
            FROM alerts
        """ + where + """
            GROUP BY source_ip
            ORDER BY total DESC LIMIT 10
        """, tuple(params))

        sources = cursor.fetchall()

        return jsonify({
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
            "alerts": alerts,
            "counts": counts,
            "status_counts": status_counts,
            "open_alerts": status_counts["Open"],
            "threat_categories": categories,
            "top_sources": sources
        })

    finally:
        cursor.close()
        connection.close()


@advanced.route("/api/alerts/<int:alert_id>/related")
def related_alerts(alert_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM alerts WHERE id = %s",
            (alert_id,)
        )

        alert = cursor.fetchone()

        if alert is None:
            return jsonify({"error": "Alert not found"}), 404

        if not alert["source_ip"]:
            return jsonify({"alerts": []})

        cursor.execute("""
            SELECT id, source_ip, destination_ip,
                   signature, severity, status, created_at
            FROM alerts
            WHERE source_ip = %s
              AND id != %s
              AND created_at BETWEEN
                  DATE_SUB(%s, INTERVAL 10 MINUTE)
                  AND DATE_ADD(%s, INTERVAL 10 MINUTE)
            ORDER BY created_at DESC
            LIMIT 50
        """, (
            alert["source_ip"],
            alert_id,
            alert["created_at"],
            alert["created_at"]
        ))

        return jsonify({"alerts": cursor.fetchall()})

    finally:
        cursor.close()
        connection.close()


@advanced.route("/api/alerts/<int:alert_id>/mitre")
def mitre_details(alert_id):
    from agents.mitre import classify_mitre

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT signature FROM alerts WHERE id = %s",
            (alert_id,)
        )

        alert = cursor.fetchone()

        if alert is None:
            return jsonify({"error": "Alert not found"}), 404

        return jsonify(classify_mitre(alert["signature"]))

    finally:
        cursor.close()
        connection.close()


@advanced.route("/api/alerts/export")
def export_alerts():
    where, params = build_filters()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    fields = [
        "id",
        "event_timestamp",
        "event_source",
        "created_at",
        "source_ip",
        "destination_ip",
        "source_port",
        "destination_port",
        "protocol",
        "signature",
        "category",
        "original_severity",
        "severity",
        "related_alerts",
        "priority",
        "recommended_response",
        "status"
    ]

    def safe_cell(value):
        if value is None:
            return ""

        if isinstance(value, str):
            if value.lstrip().startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                return "'" + value

        return value

    try:
        cursor.execute(
            "SELECT * FROM alerts" + where +
            " ORDER BY id DESC",
            tuple(params)
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)

        for alert in cursor:
            writer.writerow([
                safe_cell(alert.get(field))
                for field in fields
            ])

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=sentinel-alerts.csv"
            }
        )

    finally:
        cursor.close()
        connection.close()
