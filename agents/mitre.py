MAPPINGS = [
    (
        ("brute force", "bruteforce", "password guessing"),
        "T1110",
        "Brute Force",
        "Credential Access"
    ),
    (
        ("port scan", "network scan"),
        "T1046",
        "Network Service Discovery",
        "Discovery"
    ),
    (
        ("syn flood", "udp flood", "icmp flood",
         "denial of service", "ddos"),
        "T1498",
        "Network Denial of Service",
        "Impact"
    ),
    (
        ("arp spoof", "arp poisoning"),
        "T1557.002",
        "ARP Cache Poisoning",
        "Credential Access / Collection"
    ),
    (
        ("dns tunnel",),
        "T1071.004",
        "DNS",
        "Command and Control"
    ),
    (
        ("sql injection", "sqli", "directory traversal"),
        "T1190",
        "Exploit Public-Facing Application",
        "Initial Access"
    ),
    (
        ("cross-site scripting", "xss"),
        "T1189",
        "Drive-by Compromise",
        "Initial Access"
    )
]


def classify_mitre(signature):
    signature = str(signature or "").lower()

    for keywords, technique, name, tactic in MAPPINGS:
        if any(word in signature for word in keywords):
            return {
                "technique": technique,
                "name": name,
                "tactic": tactic,
                "confidence": "Heuristic",
                "url": (
                    "https://attack.mitre.org/techniques/"
                    + technique.replace(".", "/") + "/"
                )
            }

    return {
        "technique": None,
        "name": "Unclassified",
        "tactic": "Unknown",
        "confidence": "None",
        "url": None
    }
