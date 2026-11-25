import argparse
import json
import time
from pathlib import Path
from collectors.normalize import normalize


def monitor(source, input_path, output_path):
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"[COLLECTOR] Monitoring {source}: {input_path}")

    with open(input_path) as input_file:
        input_file.seek(0, 2)

        with destination.open("a", buffering=1) as output:
            while True:
                position = input_file.tell()
                line = input_file.readline()

                if not line or not line.endswith("\n"):
                    input_file.seek(position)
                    time.sleep(0.5)
                    continue

                try:
                    event = json.loads(line)
                    normalized = normalize(event, source)

                    if normalized is not None:
                        output.write(
                            json.dumps(normalized) + "\n"
                        )

                        print(f"[{source.upper()}] Alert received")

                except (ValueError, TypeError, AttributeError):
                    continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        choices=["suricata", "snort", "wazuh"],
        required=True
    )

    parser.add_argument("--input", required=True)

    parser.add_argument(
        "--output",
        default="logs/unified.json"
    )

    args = parser.parse_args()

    try:
        monitor(args.source, args.input, args.output)
    except KeyboardInterrupt:
        print("\n[COLLECTOR] Stopped")
