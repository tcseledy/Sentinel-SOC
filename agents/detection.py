import time
from collections import defaultdict, deque


class ThreatCorrelation:

    def __init__(self, window=60):
        self.window = window
        self.events = defaultdict(deque)

    def analyze(self, source_ip, severity):
        if not isinstance(source_ip, str) or not source_ip:
            return severity, 0

        now = time.monotonic()
        history = self.events[source_ip]

        while history and now - history[0] > self.window:
            history.popleft()

        history.append(now)
        count = len(history)

        if count >= 10:
            severity = "Critical"
        elif count >= 5 and severity != "Critical":
            severity = "High"

        return severity, count
