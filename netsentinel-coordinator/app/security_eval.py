def validate_alert_payload(alert_json: dict) -> bool:
    """Scans the values in the JSON for common prompt injection signatures."""
    forbidden_phrases = [
        "ignore previous instructions",
        "system prompt",
        "bypass",
        "forget all instructions",
        "ignore all previous"
    ]
    
    def check_values(data):
        if isinstance(data, dict):
            for v in data.values():
                check_values(v)
        elif isinstance(data, list):
            for item in data:
                check_values(item)
        elif isinstance(data, str):
            lower_val = data.lower()
            for phrase in forbidden_phrases:
                if phrase in lower_val:
                    raise ValueError(f"Security Alert: Potential prompt injection detected. Forbidden phrase found: '{phrase}'")
                    
    check_values(alert_json)
    return True
