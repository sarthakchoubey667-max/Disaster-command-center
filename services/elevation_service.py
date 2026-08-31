import os
import requests

from services.external_base import DEFAULT_TIMEOUT, result, unavailable


def get_elevation(latitude: float, longitude: float) -> dict:
    key = os.getenv("OPENTOPOGRAPHY_API_KEY")
    if not key:
        return unavailable("OpenTopography", "OPENTOPOGRAPHY_API_KEY is not configured", {"elevation_m": None})
    try:
        response = requests.get(os.getenv("OPENTOPOGRAPHY_API_URL", "https://portal.opentopography.org/API/globaldem"), timeout=DEFAULT_TIMEOUT, params={"demtype": os.getenv("OPENTOPOGRAPHY_DEM_TYPE", "SRTMGL1"), "south": latitude - 0.001, "north": latitude + 0.001, "west": longitude - 0.001, "east": longitude + 0.001, "outputFormat": "AAIGrid", "API_Key": key})
        response.raise_for_status()
        rows = [line.split() for line in response.text.splitlines() if line and not line.lower().startswith(("ncols", "nrows", "xll", "yll", "cellsize", "nodata"))]
        values = [float(value) for row in rows for value in row if value != "-9999"]
        elevation = round(sum(values) / len(values), 2) if values else None
        return result("OpenTopography", data={"elevation_m": elevation, "sample_count": len(values), "dem_type": os.getenv("OPENTOPOGRAPHY_DEM_TYPE", "SRTMGL1")})
    except Exception:
        return unavailable("OpenTopography", "Elevation provider is currently unavailable", {"elevation_m": None})
