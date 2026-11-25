import argparse
import json
import subprocess
from pathlib import Path


def collect_remote(host, remote_path, local_path):
    destination = Path(local_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ssh", "-T", "--", host,
        "tail", "-n", "0", "-F", "--", remote_path
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    print("[COLLECTOR] Connected to remote log stream")

    try:
        with destination.open("a", buffering=1) as output:
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(event, dict):
                    continue

                if event.get("event_type") != "alert":
                    continue

                output.write(json.dumps(event) + "\n")
                print("[COLLECTOR] Alert received")

    except KeyboardInterrupt:
        print("\n[COLLECTOR] Stopping")

    finally:
        process.terminate()
        process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("host")

    parser.add_argument(
        "--remote-log",
        default="/var/log/suricata/eve.json"
    )

    parser.add_argument(
        "--output",
        default="logs/remote-suricata.json"
    )

    args = parser.parse_args()

    collect_remote(
        args.host,
        args.remote_log,
        args.output
    )
