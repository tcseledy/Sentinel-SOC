from flask import Flask, render_template, jsonify, request
from database.connection import get_connection

app = Flask(__name__)

from dashboard.advanced import advanced
app.register_blueprint(advanced)



def fetch_dashboard_data():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT severity, COUNT(*) AS total
            FROM alerts
            GROUP BY severity
        """)

        counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "Unknown": 0
        }

        for row in cursor.fetchall():
            counts[row["severity"]] = row["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM alerts
            WHERE status = 'Open'
        """)

        open_alerts = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT *
            FROM alerts
            ORDER BY id DESC
            LIMIT 100
        """)

        alerts = cursor.fetchall()


        cursor.execute("""
            SELECT COALESCE(NULLIF(category, ''), 'Uncategorized') AS category,
                   COUNT(*) AS total
            FROM alerts
            GROUP BY COALESCE(NULLIF(category, ''), 'Uncategorized')
            ORDER BY total DESC
        """)

        threat_categories = cursor.fetchall()

        cursor.execute("""
            SELECT source_ip, COUNT(*) AS total
            FROM alerts
            WHERE source_ip IS NOT NULL
            GROUP BY source_ip
            ORDER BY total DESC
            LIMIT 10
        """)

        top_sources = cursor.fetchall()


        cursor.execute("""
            SELECT status, COUNT(*) AS total
            FROM alerts
            GROUP BY status
        """)

        status_counts = {
            "Open": 0,
            "Investigating": 0,
            "Resolved": 0
        }

        for row in cursor.fetchall():
            status_counts[row["status"]] = row["total"]

        return {
            "total": sum(counts.values()),
            "counts": counts,
            "open_alerts": open_alerts,
            "alerts": alerts,
            "status_counts": status_counts,
            "threat_categories": threat_categories,
            "top_sources": top_sources
        }

    finally:
        cursor.close()
        connection.close()


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/alerts")
def api_alerts():
    return jsonify(fetch_dashboard_data())



@app.route("/api/alerts/<int:alert_id>/status", methods=["PATCH"])
def update_alert_status(alert_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("Open", "Investigating", "Resolved"):
        return jsonify({"error": "Invalid status"}), 400

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM alerts WHERE id = %s",
            (alert_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Alert not found"}), 404

        cursor.execute(
            "UPDATE alerts SET status = %s WHERE id = %s",
            (status, alert_id)
        )

        connection.commit()
        return jsonify({"success": True, "status": status})

    finally:
        cursor.close()
        connection.close()



@app.route("/api/alerts/page")
def paginated_alerts():
    page = max(1, request.args.get("page", 1, type=int))
    limit = request.args.get("limit", 30, type=int)

    if limit not in (15, 30, 50, 100):
        limit = 30

    search = request.args.get("search", "").strip()
    severity = request.args.get("severity", "All")
    status = request.args.get("status", "All")

    conditions = []
    params = []

    if search:
        conditions.append("""
            (CAST(id AS CHAR) LIKE %s
            OR source_ip LIKE %s
            OR destination_ip LIKE %s
            OR signature LIKE %s)
        """)
        params.extend(["%" + search + "%"] * 4)

    if severity != "All":
        conditions.append("severity = %s")
        params.append(severity)

    if status != "All":
        conditions.append("status = %s")
        params.append(status)

    where = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

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
        offset = (page - 1) * limit

        cursor.execute(
            "SELECT * FROM alerts" + where +
            " ORDER BY id DESC LIMIT %s OFFSET %s",
            tuple(params + [limit, offset])
        )

        return jsonify({
            "alerts": cursor.fetchall(),
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit
        })

    finally:
        cursor.close()
        connection.close()



@app.route("/api/alerts/timeline")
def alert_timeline():
    import time

    ranges = {
        "1h": (3600, 300),
        "24h": (86400, 3600),
        "7d": (604800, 21600),
        "30d": (2592000, 86400)
    }

    selected = request.args.get("range", "24h")

    if selected not in ranges:
        selected = "24h"

    duration, interval = ranges[selected]

    now = int(time.time())
    start = now - duration

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                FLOOR((CAST(UNIX_TIMESTAMP(created_at)
                    AS SIGNED) - %s) / %s) AS bucket,
                COUNT(*) AS total
            FROM alerts
            WHERE created_at >= FROM_UNIXTIME(%s)
              AND created_at < FROM_UNIXTIME(%s)
            GROUP BY bucket
            ORDER BY bucket
        """, (start, interval, start, now))

        counts = {
            int(row["bucket"]): int(row["total"])
            for row in cursor.fetchall()
        }

        timeline = [
            {
                "timestamp": start + i * interval,
                "total": counts.get(i, 0)
            }
            for i in range(duration // interval)
        ]

        return jsonify({
            "range": selected,
            "interval": interval,
            "timeline": timeline,
            "total": sum(item["total"] for item in timeline)
        })

    finally:
        cursor.close()
        connection.close()



@app.route("/api/alerts/<int:alert_id>")
def get_alert_details(alert_id):
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

        return jsonify(alert)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
