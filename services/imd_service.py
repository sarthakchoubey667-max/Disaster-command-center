import requests


# IMD API base URL
IMD_BASE_URL = "https://api.imd.gov.in"


def get_imd_data(endpoint: str):
    """
    Generic IMD API request.
    """

    url = f"{IMD_BASE_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        return {
            "success": True,
            "data": response.json()
        }

    except requests.exceptions.RequestException as e:

        return {
            "success": False,
            "error": str(e)
        }