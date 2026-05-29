from datetime import datetime, timedelta, timezone


ALERT_EXPIRY_HOURS = 24


def generate_expiry():
    return (
        datetime.now(timezone.utc) +
        timedelta(hours=ALERT_EXPIRY_HOURS)
    ).isoformat()


def is_expired(alert: dict) -> bool:
    expires_at = alert.get("expires_at")

    if not expires_at:
        return False

    try:
        expiry = datetime.fromisoformat(
            expires_at.replace("Z", "+00:00")
        )

        return datetime.now(timezone.utc) > expiry

    except Exception:
        return False


def update_lifecycle(alert: dict) -> dict:
    risk_score = int(alert.get("risk_score", 50))
    velocity = alert.get("velocity", "stable")

    if is_expired(alert):
        alert["status"] = "expired"
        return alert

    if risk_score >= 80:
        alert["status"] = "escalating"

    elif risk_score >= 65:
        alert["status"] = "active"

    elif velocity == "watch":
        alert["status"] = "monitoring"

    else:
        alert["status"] = "cooling"

    if not alert.get("expires_at"):
        alert["expires_at"] = generate_expiry()

    return alert
