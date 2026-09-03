# DisasterAI Command Center

FastAPI + React command center with the existing five-second controlled sensor simulation, flood ML/risk engine, GIS dashboard, alerts, and a resilient external-data layer for landslide intelligence.

## External integrations

- OpenWeather: `/api/external/weather`
- USGS earthquakes: `/api/external/earthquakes`
- OpenTopography DEM/elevation: `/api/external/elevation`
- Google geocoding: `/api/external/geocode` and `/api/external/reverse-geocode`
- NDMA SACHET RSS alerts: `/api/external/alerts`
- NWDP/NWIC water data: `/api/external/river`
- Planet satellite scene search: `/api/external/satellite`
- Unified landslide input: `/api/data-fusion`
- Geo-tagged field reports: `GET/POST /api/field-reports`
- Landslide-specific risk: `/api/landslide/risk`
- Alert-delivery readiness: `/api/notifications/status`

Adapters return consistent `status`, `source`, `timestamp`, and `data` fields. Missing credentials/provider failures return `status: "fallback"` without stopping FastAPI or the simulation. Fusion calls sources concurrently and returns normalized `landslide_features` plus availability details.

## Local development

Copy `.env.example` to `.env`, fill only credentials you have, and never commit `.env`.

```powershell
python -m uvicorn backend.main:app --reload
npm install
npm run dev
```

The dashboard still polls `/api/dashboard` every five seconds. External fusion loads once per page load to avoid unnecessary provider usage.

Field officers can submit geo-tagged crack, slope movement, landslide, flooding, and blocked-road reports with an optional photo/video. Reports are stored in SQLite and displayed on the GIS map. The frontend is installable as a PWA; text/coordinate reports submitted without a network connection are queued on the device and synchronized when connectivity returns.

## Verification

```powershell
python -m unittest discover -p "test_*.py"
npm run lint
npm run build
```

## Render

Backend build: `pip install -r backend/requirements.txt`

Backend start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Set backend variables: `OPENWEATHER_API_KEY`, `OPENTOPOGRAPHY_API_KEY`, `GOOGLE_MAPS_API_KEY`, `PLANET_CLIENT_ID`, `PLANET_CLIENT_SECRET`, optional `NWIC_API_URL`/`NWIC_API_TOKEN`, and verified official `SACHET_FEED_URL`. Optional URL overrides are listed in `.env.example`. USGS requires no key. Without a private NWIC endpoint, the river adapter uses NWIC's official open Assam 2026-2030 hourly telemetry CSV and caches it for 15 minutes. Planet OAuth uses the Catalog API and defaults to public Sentinel-2 L2A metadata; the legacy `PLANET_API_KEY` path remains available for compatible paid accounts.

When OpenTopography is unavailable or rate-limited, elevation falls back to the Open-Meteo Elevation API (Copernicus DEM GLO-90) with attribution. When Google Geocoding is not configured, reverse geocoding falls back to the public OpenStreetMap Nominatim service with a project User-Agent, a one-request-per-second limit, 24-hour caching, and visible OpenStreetMap attribution. Review provider terms before commercial or high-traffic deployment.

Frontend build: `npm install && npm run build`; publish `dist`; set `VITE_API_BASE_URL=https://YOUR-BACKEND.onrender.com`.

For durable field reports and media on Render, attach a persistent disk and set `DISASTER_DATA_DIR` to its mount path (for example `/var/data/disaster-ai`). Without a persistent disk, SQLite records and uploaded media can be lost when the service restarts or redeploys. `MAX_REPORT_UPLOAD_MB` defaults to `10`.

## Landslide model

The fusion endpoint now uses a landslide-specific predictor. It loads `LANDSLIDE_MODEL_PATH` when a trained model is present and otherwise returns a clearly labelled `transparent_heuristic_fallback`. Train only from verified historical records matching `ml/landslide_training_template.csv`:

```powershell
python ml/train_landslide_model.py path/to/verified-landslides.csv
```

The target column is `landslide_event` (`0` or `1`). Do not describe the heuristic fallback as a trained ML model.

## Automated warning delivery

In-app multilingual warnings and opt-in browser notifications work without credentials. Automated SMS is disabled by default. To enable it, set `ALERT_DELIVERY_ENABLED=true`, comma-separated `ALERT_RECIPIENTS`, and `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`. The backend checks every `ALERT_MONITOR_INTERVAL_SECONDS`, sends only above `ALERT_RISK_THRESHOLD`, and applies `ALERT_COOLDOWN_SECONDS` to prevent repeated messages. Protect recipient consent and comply with telecom rules before enabling delivery.

Keep provider keys backend-only. Never put secrets in `VITE_*` variables because Vite embeds them in browser assets.
