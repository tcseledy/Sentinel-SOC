import os
from database.storage import save_alert
import json
import time
from agents.detection import ThreatCorrelation
from agents.response import recommend_response
from collectors.suricata import classify_severity


def monitor_alerts(log_path):
    correlation = ThreatCorrelation()
    print(f"[MONITOR] Watching: {log_path}")
    print("[MONITOR] Waiting for new alerts...")
    print("[MONITOR] Press Ctrl+C to stop.")

    try:
        with open(log_path, "r") as file:
            file.seek(0, 2)

            while True:
                position = file.tell()
                line = file.readline()

                if not line or not line.endswith("\n"):
                    file.seek(position)
                    time.sleep(1)
                    continue

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

                severity = classify_severity(
                    alert.get("severity")
                )

                event["event_source"] = os.getenv(
                    "SOC_EVENT_SOURCE", "Unknown"
                )

                original_severity = severity
                severity, count = correlation.analyze(
                    event.get("src_ip"), severity
                )
                response = recommend_response(
                    alert.get("signature"), severity
                )

                print("\n" + "=" * 45)
                print(f"[{severity.upper()}] NEW SECURITY ALERT")
                print("=" * 45)
                print(f"Timestamp: {event.get('timestamp')}")
                print(f"Source: {event.get('src_ip')}")
                print(f"Destination: {event.get('dest_ip')}")
                print(f"Protocol: {event.get('proto')}")
                print(f"Signature: {alert.get('signature')}")
                print(f"Category: {alert.get('category')}")
                try:
                    alert_id = save_alert(
                        event, original_severity,
                        severity, count, response
                    )
                    print(f"[DATABASE] Alert saved with ID: {alert_id}")
                except Exception as error:
                    print(f"[DATABASE ERROR] {error}")

                print(f"Related alerts: {count}")
                print(f"Priority: {response['priority']}")
                print(f"Response: {response['action']}")
                print("=" * 45, flush=True)

    except KeyboardInterrupt:
        print("\n[MONITOR] Monitoring stopped.")

    except FileNotFoundError:
        print(f"[ERROR] Log file not found: {log_path}")

    except PermissionError:
        print(f"[ERROR] Permission denied: {log_path}")
