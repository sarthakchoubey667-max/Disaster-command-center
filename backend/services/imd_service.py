import os
import requests
from datetime import datetime


IMD_API_URL = "https://api.imd.gov.in/api/v1/current_wx"


def get_imd_data():
    """
    Fetch current weather data from IMD.

    If an API key is not available, return simulation data
    so the Disaster Command Center continues working.
    """

    api_key = os.getenv("IMD_API_KEY")

    # ---------------------------------------
    # No API key -> simulation mode
    # ---------------------------------------
    if not api_key:
        return {
            "success": True,
            "source": "simulation",
            "data": {
                "temperature": 28,
                "humidity": 80,
                "wind_speed": 15,
                "rainfall": 185,
                "timestamp": datetime.now().isoformat()
            }
        }

    # ---------------------------------------
    # Real IMD API
    # ---------------------------------------
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }

        response = requests.get(
            IMD_API_URL,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        return {
            "success": True,
            "source": "IMD",
            "data": response.json()
        }

    except requests.exceptions.RequestException as e:

        return {
            "success": False,
            "source": "IMD",
            "error": str(e)
        }