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
    telegram_chats = [value.strip() for value in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if value.strip()]
    sms_configured = all([os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"), os.getenv("TWILIO_FROM_NUMBER"), recipients])
    telegram_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN") and telegram_chats)
    master_enabled = os.getenv("ALERT_DELIVERY_ENABLED", "false").lower() == "true"
    telegram_enabled = master_enabled and os.getenv("TELEGRAM_ALERTS_ENABLED", "false").lower() == "true" and telegram_configured
    return {
        "enabled": master_enabled and (sms_configured or telegram_enabled),
        "sms_configured": sms_configured,
        "recipient_count": len(recipients),
        "telegram_configured": telegram_configured,
        "telegram_enabled": telegram_enabled,
        "telegram_chat_count": len(telegram_chats),
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


def maybe_dispatch_alerts(risk: dict, location: str = "Monitored zone"):
    """Deliver a threshold alert through every configured channel."""
    global _last_sent_at, _last_result
    status = notification_status()
    if not status["enabled"]:
        return {"status": "disabled", **status}
    score = float(risk.get("score", 0))
    if score < status["threshold"]:
        return {"status": "below_threshold", "score": score}
    with _lock:
        if time.monotonic() - _last_sent_at < status["cooldown_seconds"]:
            return {"status": "cooldown", "score": score}
        level = risk.get("level", "WARNING")
        message = f"⚠️ DisasterAI {level}\nLandslide risk: {score:.1f}/100\nLocation: {location}\nAvoid unstable slopes and follow official evacuation instructions."
        channels, errors = {}, {}

        if status["telegram_enabled"]:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            delivered = 0
            for chat_id in [value.strip() for value in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if value.strip()]:
                try:
                    response = requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": message},
                        timeout=DEFAULT_TIMEOUT,
                    )
                    response.raise_for_status()
                    if not response.json().get("ok"):
                        raise RuntimeError("Telegram rejected the alert")
                    delivered += 1
                except Exception as error:
                    errors["telegram"] = type(error).__name__
            channels["telegram"] = {"delivered": delivered, "requested": status["telegram_chat_count"]}

        if status["sms_configured"]:
            try:
                sms_result = _send_sms_message(message)
                channels["sms"] = sms_result
            except Exception as error:
                errors["sms"] = type(error).__name__

        delivered = sum(item.get("delivered", item.get("count", 0)) for item in channels.values())
        if delivered:
            _last_sent_at = time.monotonic()
        _last_result = {"status": "sent" if delivered else "failed", "score": score, "channels": channels, "errors": errors}
        return _last_result


def _send_sms_message(message: str) -> dict:
    sid, token = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    sender = os.getenv("TWILIO_FROM_NUMBER")
    recipients = [value.strip() for value in os.getenv("ALERT_RECIPIENTS", "").split(",") if value.strip()]
    delivered = 0
    for recipient in recipients:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=HTTPBasicAuth(sid, token), timeout=DEFAULT_TIMEOUT,
            data={"From": sender, "To": recipient, "Body": message},
        )
        response.raise_for_status()
        delivered += 1
    return {"delivered": delivered, "requested": len(recipients)}
