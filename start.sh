#!/bin/bash

set -e

cd "$(dirname "$0")"

INTERFACE="${1:-en0}"
CONFIG="/opt/homebrew/etc/suricata/suricata.yaml"

source .venv/bin/activate

LOCK="logs/.sentinel-running"
mkdir -p logs

if ! mkdir "$LOCK" 2>/dev/null; then
    echo "[ERROR] Startup lock exists."
    exit 1
fi

IDS_PID=""
MONITOR_PID=""
DASHBOARD_PID=""

cleanup() {
    trap - EXIT INT TERM
    echo "[STOP] Shutting down Sentinel SOC..."

    for pid in "$MONITOR_PID" "$DASHBOARD_PID"; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    if [ -n "$IDS_PID" ]; then
        sudo kill -TERM "$IDS_PID" 2>/dev/null || true
    fi

    wait 2>/dev/null || true
    rmdir "$LOCK" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT TERM

echo "[START] Sentinel SOC"

if lsof -nP -iTCP:8080 -sTCP:LISTEN >/dev/null; then
    echo "[ERROR] Port 8080 is already occupied."
    exit 1
fi

if pgrep -x suricata >/dev/null; then
    echo "[ERROR] Suricata is already running."
    exit 1
fi

ifconfig "$INTERFACE" >/dev/null

echo "[CHECK] MySQL connection"

python -c '
from database.connection import get_connection
conn = get_connection()
conn.close()
print("[PASS] MySQL connected")
'

sudo -v

RUN_DIR="$(mktemp -d "$PWD/logs/live.XXXXXX")"
touch "$RUN_DIR/eve.json"

echo "[START] Live alert monitor"

SOC_EVENT_SOURCE="Live - Suricata" \
python -u main.py --live --log "$RUN_DIR/eve.json" &
MONITOR_PID=$!

sleep 2
kill -0 "$MONITOR_PID"

echo "[START] Suricata on $INTERFACE"

sudo -n suricata \
    -c "$CONFIG" \
    -i "$INTERFACE" \
    -s "$PWD/rules/local.rules" \
    -l "$RUN_DIR" &
IDS_PID=$!

echo "[START] Flask dashboard"

python -m flask --app dashboard.app run \
    --host 127.0.0.1 --port 8080 &
DASHBOARD_PID=$!

sleep 5

kill -0 "$IDS_PID"
kill -0 "$DASHBOARD_PID"

curl -fsS http://127.0.0.1:8080/ >/dev/null

open http://127.0.0.1:8080

echo "[RUNNING] Sentinel SOC"
echo "Interface: $INTERFACE"
echo "Dashboard: http://127.0.0.1:8080"
echo "Press Ctrl+C to shut down."

while true; do
    kill -0 "$IDS_PID"
    kill -0 "$MONITOR_PID"
    kill -0 "$DASHBOARD_PID"
    sleep 2
done
