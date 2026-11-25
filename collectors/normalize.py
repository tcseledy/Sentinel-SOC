def normalize(event, source):
    if not isinstance(event, dict):
        return None

    if source == "suricata":
        if event.get("event_type") != "alert":
            return None
        return event

    if source == "snort":
        priority = event.get("priority")

        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = None

        return {
            "event_type": "alert",
            "timestamp": event.get("timestamp"),
            "src_ip": event.get("src_addr"),
            "dest_ip": event.get("dst_addr"),
            "src_port": event.get("src_port"),
            "dest_port": event.get("dst_port"),
            "proto": event.get("proto"),
            "alert": {
                "signature": event.get("msg", "Snort Alert"),
                "category": event.get("class", "Snort"),
                "severity": priority
            }
        }

    if source == "wazuh":
        rule = event.get("rule") or {}
        data = event.get("data") or {}
        agent = event.get("agent") or {}

        try:
            level = int(rule.get("level", 0))
        except (ValueError, TypeError):
            level = 0

        if level >= 12:
            severity = 1
        elif level >= 7:
            severity = 2
        else:
            severity = 3

        return {
            "event_type": "alert",
            "timestamp": event.get("timestamp"),
            "src_ip": data.get("srcip"),
            "dest_ip": data.get("dstip") or agent.get("ip"),
            "src_port": data.get("srcport"),
            "dest_port": data.get("dstport"),
            "proto": data.get("protocol"),
            "alert": {
                "signature": rule.get(
                    "description", "Wazuh Alert"
                ),
                "category": "Wazuh",
                "severity": severity
            }
        }

    return None
