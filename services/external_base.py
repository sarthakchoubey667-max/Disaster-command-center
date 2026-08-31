"""Shared helpers for resilient external-data adapters."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_TIMEOUT = float(os.getenv("EXTERNAL_API_TIMEOUT_SECONDS", "8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def result(source: str, *, data: Any = None, status: str = "success", message: str | None = None) -> dict:
    payload = {
        "status": status,
        "source": source,
        "timestamp": utc_now(),
        "data": data,
    }
    if message:
        payload["message"] = message
    return payload


def unavailable(source: str, message: str, fallback: Any = None) -> dict:
    return result(source, status="fallback", message=message, data=fallback)


def request_json(method: str, url: str, **kwargs) -> Any:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()
