import json
import argparse
from collectors.suricata import collect_alerts
from agents.monitor import monitor_alerts
from config import SURICATA_LOG


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel SOC Platform"
    )

    parser.add_argument(
        "--log",
        default=str(SURICATA_LOG),
        help="Path to Suricata JSON log"
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable real-time monitoring"
    )

    args = parser.parse_args()

    print("=" * 45)
    print("SENTINEL - Security Operations Center")
    print("=" * 45)

    if args.live:
        monitor_alerts(args.log)
    else:
        alerts = collect_alerts(args.log)

        print(f"Total alerts detected: {len(alerts)}")

        for alert in alerts:
            print(json.dumps(alert, indent=4))


if __name__ == "__main__":
    main()
