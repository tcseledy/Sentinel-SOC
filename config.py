import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent

LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

SURICATA_LOG = Path(os.getenv(
    "SURICATA_LOG",
    "/var/log/suricata/eve.json"
))

SNORT_LOG = Path(os.getenv(
    "SNORT_LOG",
    "/var/log/snort/alert_json.txt"
))

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000

MONITOR_INTERVAL = 5
