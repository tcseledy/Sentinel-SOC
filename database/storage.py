from database.connection import get_connection


def save_alert(event, original_severity, severity, count, response):
    alert = event.get("alert", {})

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO alerts (
                event_timestamp,
                source_ip,
                destination_ip,
                source_port,
                destination_port,
                protocol,
                signature,
                category,
                original_severity,
                severity,
                related_alerts,
                priority,
                recommended_response,
                event_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            event.get("timestamp"),
            event.get("src_ip"),
            event.get("dest_ip"),
            event.get("src_port"),
            event.get("dest_port"),
            event.get("proto"),
            alert.get("signature"),
            alert.get("category"),
            original_severity,
            severity,
            count,
            response.get("priority"),
            response.get("action"),
            event.get("event_source", "Unknown")
        )

        cursor.execute(query, values)
        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
