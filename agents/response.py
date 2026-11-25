def recommend_response(signature, severity):
    signature = str(signature or "").lower()

    if "syn flood" in signature:
        action = "Investigate traffic volume and consider rate limiting."

    elif "brute force" in signature:
        action = "Review authentication logs and investigate source IP."

    elif "port scan" in signature:
        action = "Investigate reconnaissance and exposed services."

    elif "dns" in signature:
        action = "Investigate DNS queries and domain reputation."

    elif "https" in signature:
        action = "Review HTTPS connection metadata and endpoint logs."

    else:
        action = "Review security logs and investigate the event."

    priorities = {
        "Critical": "Immediate investigation",
        "High": "Urgent investigation",
        "Medium": "Scheduled investigation",
        "Low": "Continue monitoring",
        "Unknown": "Manual review"
    }

    return {
        "priority": priorities.get(severity, "Manual review"),
        "action": action
    }
