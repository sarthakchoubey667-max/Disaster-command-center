import os
import threading
import time

import requests
from requests.auth import HTTPBasicAuth

from services.external_base import DEFAULT_TIMEOUT


_lock = threading.Lock()
_last_sent_at = 0.0
_last_result = None


def notification_status():
    recipients = [value.strip() for value in os.getenv("ALERT_RECIPIENTS", "").split(",") if value.strip()]
    configured = all([os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"), os.getenv("TWILIO_FROM_NUMBER"), recipients])
    return {
        "enabled": os.getenv("ALERT_DELIVERY_ENABLED", "false").lower() == "true",
        "sms_configured": configured,
        "recipient_count": len(recipients),
        "threshold": float(os.getenv("ALERT_RISK_THRESHOLD", "60")),
        "cooldown_seconds": int(os.getenv("ALERT_COOLDOWN_SECONDS", "3600")),
        "last_result": _last_result,
    }


def maybe_dispatch_sms(risk: dict, location: str = "Monitored zone"):
    global _last_sent_at, _last_result
    status = notification_status()
    if not status["enabled"] or not status["sms_configured"]:
        return {"status": "disabled", **status}
    score = float(risk.get("score", 0))
    if score < status["threshold"]:
        return {"status": "below_threshold", "score": score}
    with _lock:
        if time.monotonic() - _last_sent_at < status["cooldown_seconds"]:
            return {"status": "cooldown", "score": score}
        sid, token = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
        sender = os.getenv("TWILIO_FROM_NUMBER")
        recipients = [value.strip() for value in os.getenv("ALERT_RECIPIENTS", "").split(",") if value.strip()]
        message = f"DisasterAI {risk.get('level', 'WARNING')}: landslide risk {score:.1f}/100 at {location}. Avoid unstable slopes and follow official instructions."
        outcomes = []
        for recipient in recipients:
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=HTTPBasicAuth(sid, token), timeout=DEFAULT_TIMEOUT,
                data={"From": sender, "To": recipient, "Body": message},
            )
            response.raise_for_status()
            outcomes.append({"recipient": recipient[-4:].rjust(len(recipient), "*"), "status": response.json().get("status", "queued")})
        _last_sent_at = time.monotonic()
        _last_result = {"status": "sent", "count": len(outcomes), "score": score, "outcomes": outcomes}
        return _last_result
