import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from services.data_fusion_service import get_fused_external_data
from services.weather_service import get_weather_data


class ExternalServiceTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_weather_fallback_without_key(self):
        response = get_weather_data(26.1, 91.7, {"rainfall": 80})
        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["data"]["rainfall"], 80)

    @patch("services.data_fusion_service.get_satellite_scenes")
    @patch("services.data_fusion_service.get_river_data")
    @patch("services.data_fusion_service.get_sachet_alerts")
    @patch("services.data_fusion_service.geocode")
    @patch("services.data_fusion_service.get_elevation")
    @patch("services.data_fusion_service.get_earthquakes")
    @patch("services.data_fusion_service.get_weather_data")
    def test_fusion_fallback(self, weather, quakes, elevation, geo, alerts, river, satellite):
        fallback = lambda source, data: {"status": "fallback", "source": source, "data": data}
        weather.return_value = fallback("weather", {"rainfall": 50})
        quakes.return_value = fallback("USGS", {"events": []})
        elevation.return_value = fallback("topography", None)
        geo.return_value = fallback("geocoding", None)
        alerts.return_value = fallback("alerts", {"count": 0})
        river.return_value = fallback("river", {})
        satellite.return_value = fallback("planet", {"count": 0})
        fused = get_fused_external_data(26.1, 91.7, {"rainfall": 50})
        self.assertEqual(fused["status"], "fallback")
        self.assertEqual(len(fused["fallback_sources"]), 7)
        self.assertEqual(fused["landslide_features"]["rainfall_mm"], 50)


if __name__ == "__main__":
    unittest.main()
