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

Adapters return consistent `status`, `source`, `timestamp`, and `data` fields. Missing credentials/provider failures return `status: "fallback"` without stopping FastAPI or the simulation. Fusion calls sources concurrently and returns normalized `landslide_features` plus availability details.

## Local development

Copy `.env.example` to `.env`, fill only credentials you have, and never commit `.env`.

```powershell
python -m uvicorn backend.main:app --reload
npm install
npm run dev
```

The dashboard still polls `/api/dashboard` every five seconds. External fusion loads once per page load to avoid unnecessary provider usage.

## Verification

```powershell
python -m unittest discover -p "test_*.py"
npm run lint
npm run build
```

## Render

Backend build: `pip install -r backend/requirements.txt`

Backend start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Set backend variables: `OPENWEATHER_API_KEY`, `OPENTOPOGRAPHY_API_KEY`, `GOOGLE_MAPS_API_KEY`, `PLANET_CLIENT_ID`, `PLANET_CLIENT_SECRET`, `NWIC_API_URL`, optional `NWIC_API_TOKEN`, and verified official `SACHET_FEED_URL`. Optional URL overrides are listed in `.env.example`. USGS requires no key. NWDP/NWIC may need access approval. Planet OAuth uses the Catalog API and defaults to public Sentinel-2 L2A metadata; the legacy `PLANET_API_KEY` path remains available for compatible paid accounts.

Frontend build: `npm install && npm run build`; publish `dist`; set `VITE_API_BASE_URL=https://YOUR-BACKEND.onrender.com`.

Keep provider keys backend-only. Never put secrets in `VITE_*` variables because Vite embeds them in browser assets.
