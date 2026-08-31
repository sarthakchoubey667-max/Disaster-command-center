import os
import requests
from defusedxml import ElementTree as ET

from services.external_base import DEFAULT_TIMEOUT, result, unavailable


def get_sachet_alerts(limit: int = 20) -> dict:
    url = os.getenv("SACHET_FEED_URL")
    if not url:
        return unavailable("NDMA SACHET", "SACHET_FEED_URL is not configured", {"count": 0, "alerts": []})
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        alerts = []
        entries = [node for node in root.iter() if node.tag.split("}")[-1] in ("item", "entry")]
        for item in entries[:limit]:
            values = {child.tag.split("}")[-1]: (child.text or "").strip() for child in item}
            link = values.get("link", "")
            if not link:
                link_node = next((child for child in item if child.tag.split("}")[-1] == "link"), None)
                link = link_node.attrib.get("href", "") if link_node is not None else ""
            alerts.append({"title": values.get("title", ""), "description": values.get("description") or values.get("summary", ""), "link": link, "published": values.get("pubDate") or values.get("published") or values.get("updated", ""), "guid": values.get("guid") or values.get("id", "")})
        return result("NDMA SACHET", data={"count": len(alerts), "alerts": alerts})
    except Exception:
        return unavailable("NDMA SACHET", "Official alert feed is currently unavailable", {"count": 0, "alerts": []})
