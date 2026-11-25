import json
from config import SURICATA_LOG


def classify_severity(severity):
    levels = {
        1: "High",
        2: "Medium",
        3: "Low"
    }

    if type(severity) is not int:
        return "Unknown"

    return levels.get(severity, "Unknown")


def collect_alerts(log_path=SURICATA_LOG):
    alerts = []

    try:
        with open(log_path, "r") as file:
            for line in file:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(event, dict):
                    continue

                if event.get("event_type") != "alert":
                    continue

                alert = event.get("alert", {})
                if not isinstance(alert, dict):
                    continue


                alerts.append({
                    "timestamp": event.get("timestamp"),
                    "source_ip": event.get("src_ip"),
                    "destination_ip": event.get("dest_ip"),
                    "source_port": event.get("src_port"),
                    "destination_port": event.get("dest_port"),
                    "protocol": event.get("proto"),
                    "signature": alert.get("signature"),
                    "category": alert.get("category"),
                    "severity": classify_severity(
                        alert.get("severity")
                    )
                })

    except FileNotFoundError:
        print(f"Log file not found: {log_path}")

    except PermissionError:
        print(f"Permission denied: {log_path}")

    return alerts
