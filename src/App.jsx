import {
  Activity,
  AlertTriangle,
  Bell,
  Camera,
  CloudRain,
  ContactRound,
  Droplets,
  MapPin,
  LogOut,
  Menu,
  Mountain,
  Radio,
  Satellite,
  ShieldAlert,
  Users,
  Waves,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import "./App.css";
import DisasterMap from "./DisasterMap";
import FieldReports from "./FieldReports";
import WarningCenter from "./WarningCenter";
import RescueTeams from "./RescueTeams";
import SensorChart from "./SensorChart";
import OperatorApprovals from "./OperatorApprovals";
import OperatorDirectory from "./OperatorDirectory";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||"http://127.0.0.1:8000";
const REFRESH_INTERVAL = 5000;

const DEFAULT_RECOMMENDATIONS = [
  "Evacuate vulnerable residents from Zone A.",
  "Deploy Rescue Team 2 to Sector 4.",
  "Bridge Road may become inaccessible within 30 minutes.",
  "Move Ambulance 04 closer to Government School shelter.",
];

const formatNumber = (value, digits = 1) => {
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toFixed(digits)
    : "--";
};

const formatTimestamp = (timestamp) => {
  if (!timestamp) {
    return "Waiting for live data";
  }

  const date = new Date(timestamp);

  return Number.isNaN(date.getTime())
    ? String(timestamp)
    : date.toLocaleString();
};

const normalizeArray = (value) => {
  if (Array.isArray(value)) {
    return value;
  }

  return [];
};

const supportedAlertLanguage = (alert) => {
  const text = `${alert?.title ?? ""} ${alert?.description ?? ""}`;
  if (/[\u0900-\u097f]/.test(text)) return "Hindi";
  if (/[\u0980-\u0dff]/.test(text)) return null;
  return "English";
};

function App({ session, onLogout }) {
  const [sensorData, setSensorData] = useState(null);
  const [alertsData, setAlertsData] = useState(null);
  const [aiData, setAiData] = useState(null);

  const [backendOnline, setBackendOnline] = useState(false);
  const [sensorError, setSensorError] = useState("");

  const [analyzing, setAnalyzing] = useState(false);
  const [showAIAnalysis, setShowAIAnalysis] = useState(false);

  const [aiRisk, setAiRisk] = useState(null);
  const [riskTrend, setRiskTrend] = useState(null);
  const [riskHistory, setRiskHistory] = useState([]);
  const [externalData, setExternalData] = useState(null);
  const [fieldReports, setFieldReports] = useState([]);
  const [activeSection, setActiveSection] = useState("dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [mapExpanded, setMapExpanded] = useState(false);
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [selectedSourceKey, setSelectedSourceKey] = useState(null);

  const openSection = (section) => {
    setActiveSection(section);
    setMobileNavOpen(false);
  };

  /*
   * ------------------------------------------------------------
   * LOAD DASHBOARD DATA
   * ------------------------------------------------------------
   *
   * Primary endpoint:
   *   /api/dashboard
   *
   * Fallback endpoints:
   *   /api/sensors
   *   /api/alerts
   *   /api/ai/recommendations
   *   /api/ai/risk-history
   *
   * The function is called once immediately and then every 5 sec.
   */
  const loadBackendData = useCallback(async () => {
    try {
      const dashboardResponse = await fetch(
        `${API_BASE_URL}/api/dashboard`,
        {
          cache: "no-store",
        }
      );

      if (!dashboardResponse.ok) {
        throw new Error(
          `Dashboard API returned ${dashboardResponse.status}`
        );
      }

      const dashboard = await dashboardResponse.json();

      const sensors =
        dashboard?.sensors ??
        dashboard?.sensor_data ??
        dashboard?.sensorData;

      const alerts = dashboard?.alerts;

      const recommendationsData =
        dashboard?.recommendations;

      const risk =
        dashboard?.risk?.risk ??
        dashboard?.risk;

      if (sensors) {
        setSensorData(sensors);
      }

      if (alerts) {
        setAlertsData(alerts);
      }

      if (recommendationsData) {
        setAiData(recommendationsData);
      }

      if (risk) {
        setAiRisk(risk);

        setRiskTrend(
          dashboard?.risk?.trend
            ? dashboard.risk.trend
            : {
                trend:
                  risk?.risk_direction ??
                  "STABLE",
                change:
                  risk?.risk_velocity ??
                  0,
              }
        );
      }

      setBackendOnline(true);
      setSensorError("");

      /*
       * Risk history is intentionally fetched separately.
       * This allows the dashboard endpoint to remain compatible
       * with older backend versions.
       */
      try {
        const historyResponse = await fetch(
          `${API_BASE_URL}/api/ai/risk-history`,
          {
            cache: "no-store",
          }
        );

        if (historyResponse.ok) {
          const historyData =
            await historyResponse.json();

          setRiskHistory(
            normalizeArray(historyData?.history)
          );
        }
      } catch (historyError) {
        console.warn(
          "Risk history unavailable:",
          historyError
        );
      }
    } catch (dashboardError) {
      console.warn(
        "Dashboard endpoint unavailable. Using fallback APIs.",
        dashboardError
      );

      /*
       * ----------------------------------------------------------
       * FALLBACK API MODE
       * ----------------------------------------------------------
       */
      try {
        const [
          sensorResponse,
          alertsResponse,
          aiResponse,
          historyResponse,
        ] = await Promise.all([
          fetch(`${API_BASE_URL}/api/sensors`, {
            cache: "no-store",
          }),

          fetch(`${API_BASE_URL}/api/alerts`, {
            cache: "no-store",
          }),

          fetch(
            `${API_BASE_URL}/api/ai/recommendations`,
            {
              cache: "no-store",
            }
          ),

          fetch(
            `${API_BASE_URL}/api/ai/risk-history`,
            {
              cache: "no-store",
            }
          ),
        ]);

        if (!sensorResponse.ok) {
          throw new Error(
            `Sensor API returned ${sensorResponse.status}`
          );
        }

        const sensorJson =
          await sensorResponse.json();

        setSensorData(sensorJson);

        if (alertsResponse.ok) {
          setAlertsData(
            await alertsResponse.json()
          );
        }

        if (aiResponse.ok) {
          setAiData(
            await aiResponse.json()
          );
        }

        if (historyResponse.ok) {
          const historyData =
            await historyResponse.json();

          setRiskHistory(
            normalizeArray(historyData?.history)
          );
        }

        setBackendOnline(true);
        setSensorError("");
      } catch (error) {
        console.error(
          "Backend connection failed:",
          error
        );

        setBackendOnline(false);

        setSensorError(
          "Live sensor data is unavailable. Check that the FastAPI server is running."
        );
      }
    }
  }, []);

  /*
   * ------------------------------------------------------------
   * AI INTELLIGENT PREDICTION
   * ------------------------------------------------------------
   */
  const runAIAnalysis = async () => {
    setAnalyzing(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ai/intelligent-prediction`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `AI Prediction API returned ${response.status}`
        );
      }

      const data = await response.json();

      /*
       * Provide a safe recommendation if the backend
       * doesn't return one.
       */
      if (!data?.recommended_action) {
        data.recommended_action =
          data?.risk_level === "CRITICAL"
            ? "Prioritize immediate review of the affected zone and continuously monitor incoming sensor data."
            : data?.risk_level === "HIGH"
              ? "Increase monitoring frequency and prioritize the affected zone for response planning."
              : "Continue monitoring sensor conditions and watch for an increasing risk trend.";
      }

      setAiRisk(data);

      setRiskTrend({
        trend:
          data?.risk_direction ??
          data?.acceleration_direction ??
          "STABLE",

        change:
          data?.risk_velocity ??
          data?.risk_acceleration ??
          0,
      });

      setShowAIAnalysis(true);

      /*
       * Refresh risk history after a new AI analysis.
       */
      try {
        const historyResponse = await fetch(
          `${API_BASE_URL}/api/ai/risk-history`,
          {
            cache: "no-store",
          }
        );

        if (historyResponse.ok) {
          const historyData =
            await historyResponse.json();

          setRiskHistory(
            normalizeArray(historyData?.history)
          );
        }
      } catch (historyError) {
        console.warn(
          "Unable to refresh risk history:",
          historyError
        );
      }
    } catch (error) {
      console.error(
        "AI analysis failed:",
        error
      );
    } finally {
      setAnalyzing(false);
    }
  };

  /*
   * ------------------------------------------------------------
   * LIVE 5-SECOND POLLING
   * ------------------------------------------------------------
   */
  useEffect(() => {
    let mounted = true;

    const refresh = async () => {
      if (!mounted) {
        return;
      }

      await loadBackendData();
    };

    refresh();

    const intervalId = setInterval(
      refresh,
      REFRESH_INTERVAL
    );

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [loadBackendData]);

  useEffect(() => {
    let mounted = true;
    let controller = new AbortController();

    const loadExternalData = async () => {
      controller.abort();
      controller = new AbortController();
      try {
        const response = await fetch(`${API_BASE_URL}/api/data-fusion`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Data fusion API returned ${response.status}`);
        const data = await response.json();
        if (mounted) setExternalData(data);
      } catch (error) {
        if (error.name !== "AbortError") console.warn("External data fusion unavailable:", error);
      }
    };

    loadExternalData();
    const intervalId = setInterval(loadExternalData, 30000);
    return () => {
      mounted = false;
      controller.abort();
      clearInterval(intervalId);
    };
  }, []);

  /*
   * ------------------------------------------------------------
   * DERIVED DATA
   * ------------------------------------------------------------
   */

  const operational = externalData?.operational;
  const externalSources = externalData?.sources ?? {};
  const displayedSensors = operational?.sensors
    ? { ...sensorData, ...operational.sensors }
    : sensorData;
  const officialAlerts = normalizeArray(operational?.alerts)
    .map((alert) => ({
      ...alert,
      language: supportedAlertLanguage(alert),
      level: "warning",
      location: alert?.area ?? alert?.location ?? "India",
      time: alert?.published ? formatTimestamp(alert.published) : "Official feed",
    }))
    .filter((alert) => alert.language);
  const fallbackAlerts = normalizeArray(alertsData?.alerts ?? alertsData)
    .map((alert) => ({ ...alert, language: supportedAlertLanguage(alert) }))
    .filter((alert) => alert.language);
  const alertList =
    externalSources.alerts?.status === "success" && officialAlerts.length > 0
      ? officialAlerts
      : fallbackAlerts;

  const recommendationList = normalizeArray(
    aiData?.recommendations
  );

  const displayedRecommendations =
    recommendationList.length > 0
      ? recommendationList
      : DEFAULT_RECOMMENDATIONS;

  const simulationRisk = Number(aiRisk?.adaptive_risk_score);
  const externalRisk = Number(operational?.risk?.score);
  const fusedRiskScore = Number.isFinite(simulationRisk) && Number.isFinite(externalRisk)
    ? Math.round((simulationRisk * 0.7 + externalRisk * 0.3) * 100) / 100
    : Number.isFinite(simulationRisk)
      ? simulationRisk
      : Number.isFinite(externalRisk)
        ? externalRisk
        : null;
  const fusedRiskLevel = fusedRiskScore == null
    ? "WAITING"
    : fusedRiskScore >= 80
      ? "CRITICAL"
      : fusedRiskScore >= 60
        ? "HIGH"
        : fusedRiskScore >= 35
          ? "MODERATE"
          : "LOW";

  const stats = [
    {
      title: "Overall Risk",
      value: fusedRiskScore ?? "--",
      unit: "/100",
      subtitle:
        fusedRiskLevel,
      icon: ShieldAlert,
      type: "danger",
    },

    {
      title: "People at Risk",
      value: "1,248",
      subtitle: "Across 6 zones",
      icon: Users,
      type: "warning",
    },

    {
      title: "Water Level",
      value: formatNumber(
        displayedSensors?.water_level,
        2
      ),
      unit: " m",
      subtitle: operational?.sensor_sources?.water_level ?? "Live sensor",
      icon: Droplets,
      type: "info",
    },

    {
      title: "Rainfall",
      value: formatNumber(
        displayedSensors?.rainfall,
        1
      ),
      unit: " mm",
      subtitle: operational?.sensor_sources?.rainfall ?? "Live sensor",
      icon: CloudRain,
      type: "normal",
    },
  ];

  const liveSensors = [
    {
      label: "Water Level",
      value: formatNumber(
        displayedSensors?.water_level,
        2
      ),
      unit: "m",
      note: operational?.sensor_sources?.water_level ?? "Live sensor",
    },

    {
      label: "Rainfall",
      value: formatNumber(
        displayedSensors?.rainfall,
        1
      ),
      unit: "mm",
      note: operational?.sensor_sources?.rainfall ?? "Current reading",
    },

    {
      label: "Flow Rate",
      value: formatNumber(
        displayedSensors?.flow_rate,
        1
      ),
      unit: "m³/s",
      note: operational?.sensor_sources?.flow_rate ?? "Live sensor",
    },

    {
      label: "Temperature",
      value: formatNumber(
        displayedSensors?.temperature,
        1
      ),
      unit: "°C",
      note: operational?.sensor_sources?.temperature ?? "Weather reading",
    },

    {
      label: "Humidity",
      value: formatNumber(
        displayedSensors?.humidity,
        1
      ),
      unit: "%",
      note: operational?.sensor_sources?.humidity ?? "Weather reading",
    },

    {
      label: "Wind Speed",
      value: formatNumber(
        displayedSensors?.wind_speed,
        1
      ),
      unit: "",
      note: operational?.sensor_sources?.wind_speed ?? "Weather reading",
    },
  ];

  const latestRisk =
    riskHistory.length > 0
      ? riskHistory[riskHistory.length - 1]
      : null;

  const satelliteScenes = externalSources.satellite?.data?.scenes ?? [];
  const latestSatelliteScene = [...satelliteScenes]
    .filter((scene) => scene?.acquired)
    .sort((a, b) => new Date(b.acquired) - new Date(a.acquired))[0] ?? satelliteScenes[0];
  const satelliteCollection =
    externalSources.satellite?.data?.collection ??
    latestSatelliteScene?.item_type ??
    "Waiting for coverage";

  const sourceCards = [
    { key: "weather", label: "OpenWeather", icon: CloudRain, value: externalSources.weather?.data?.description ?? "Weather intelligence", detail: `${formatNumber(externalSources.weather?.data?.rainfall_1h, 1)} mm rain · ${formatNumber(externalSources.weather?.data?.humidity, 0)}% humidity` },
    { key: "earthquakes", label: "USGS Earthquakes", icon: Activity, value: `${externalSources.earthquakes?.data?.count ?? 0} recent events`, detail: `${externalSources.earthquakes?.data?.radius_km ?? 250} km monitoring radius` },
    { key: "elevation", label: externalSources.elevation?.status === "success" ? externalSources.elevation.source : "OpenTopography", icon: Mountain, value: `${formatNumber(externalSources.elevation?.data?.elevation_m, 0)} m elevation`, detail: externalSources.elevation?.data?.attribution ?? externalSources.elevation?.data?.dem_type ?? "Terrain / DEM intelligence" },
    { key: "geocoding", label: externalSources.geocoding?.status === "success" ? externalSources.geocoding.source : "Google Geocoding", icon: MapPin, value: externalSources.geocoding?.data?.results?.[0]?.formatted_address ?? "Location resolver", detail: externalSources.geocoding?.data?.attribution ?? "Coordinate and address context" },
    { key: "alerts", label: "NDMA SACHET", icon: ShieldAlert, value: `${externalSources.alerts?.data?.count ?? 0} official alerts`, detail: "All-India government warning feed" },
    { key: "river", label: "NWDP / NWIC", icon: Waves, value: externalSources.river?.data?.water_level != null ? `${formatNumber(externalSources.river.data.water_level, 2)} m water level` : "River intelligence", detail: externalSources.river?.data?.nearest_station ? `${externalSources.river.data.nearest_station}${externalSources.river.data.river ? ` · ${externalSources.river.data.river}` : ""}` : "Government water-data network" },
    { key: "satellite", label: "Planet Satellite", icon: Satellite, value: `${externalSources.satellite?.data?.count ?? 0} scenes`, detail: latestSatelliteScene?.acquired ? `Latest: ${formatTimestamp(latestSatelliteScene.acquired)}` : "Remote-sensing coverage" },
  ];

  const operationalUses = [
    { key: "weather", target: "Sensor panel + risk engine", use: "Rainfall, humidity, temperature and wind replace simulated readings." },
    { key: "earthquakes", target: "Disaster map + seismic risk", use: "Nearby events appear on the map and magnitude contributes to risk." },
    { key: "elevation", target: "Terrain context", use: "DEM elevation is attached to the monitored landslide zone." },
    { key: "geocoding", target: "Map location resolver", use: "Fusion coordinates are converted into a readable place address." },
    { key: "alerts", target: "Active Alerts + risk engine", use: "Official warnings populate the alerts panel and alert factor." },
    { key: "river", target: "Sensor panel + water risk", use: "Nearest-station level replaces simulation and contributes to risk." },
    { key: "satellite", target: "Remote observation coverage", use: "Scene count, capture freshness and cloud cover confirm visibility." },
  ].map((usage) => ({ ...usage, source: sourceCards.find((source) => source.key === usage.key) }));
  const selectedSource = sourceCards.find((source) => source.key === selectedSourceKey);
  const selectedResponse = selectedSourceKey ? externalSources[selectedSourceKey] : null;
  const selectedUsage = operationalUses.find((usage) => usage.key === selectedSourceKey);

  /*
   * ------------------------------------------------------------
   * RENDER
   * ------------------------------------------------------------
   */
  return (
    <>
      <style>{`
        .ai-modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: rgba(2, 6, 23, 0.78);
          backdrop-filter: blur(8px);
        }

        .ai-modal {
          position: relative;
          width: min(760px, 94vw);
          max-height: min(88vh, 820px);
          overflow: auto;
          padding: 28px;
          border: 1px solid rgba(148, 163, 184, 0.22);
          border-radius: 22px;
          background: linear-gradient(
            145deg,
            #172554,
            #111a3d
          );
          color: #eef2ff;
          box-shadow:
            0 30px 90px rgba(0, 0, 0, 0.55);
        }

        .ai-modal::-webkit-scrollbar {
          width: 8px;
        }

        .ai-modal::-webkit-scrollbar-thumb {
          background: rgba(148, 163, 184, 0.35);
          border-radius: 10px;
        }

        .close-ai {
          position: absolute;
          right: 18px;
          top: 14px;
          width: 36px;
          height: 36px;
          border: 0;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.08);
          color: #fff;
          font-size: 26px;
          cursor: pointer;
        }

        .close-ai:hover {
          background: rgba(255, 255, 255, 0.15);
        }

        .ai-modal-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 20px;
          padding-right: 42px;
          margin-bottom: 22px;
        }

        .ai-modal-kicker {
          display: block;
          font-size: 11px;
          letter-spacing: 1.6px;
          color: #67e8f9;
          font-weight: 800;
          margin-bottom: 6px;
        }

        .ai-modal h2 {
          margin: 0;
          font-size: 27px;
        }

        .risk-pill {
          padding: 8px 12px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.7px;
          background: #334155;
        }

        .risk-pill.critical {
          background: #7f1d1d;
          color: #fecaca;
        }

        .risk-pill.high {
          background: #78350f;
          color: #fed7aa;
        }

        .risk-pill.moderate {
          background: #854d0e;
          color: #fef08a;
        }

        .risk-pill.low {
          background: #14532d;
          color: #bbf7d0;
        }

        .ai-score-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }

        .ai-score-row > div {
          padding: 16px;
          border-radius: 15px;
          background: rgba(15, 23, 42, 0.48);
          border: 1px solid rgba(148, 163, 184, 0.15);
        }

        .ai-score-row span,
        .ai-detail-grid span {
          display: block;
          color: #94a3b8;
          font-size: 12px;
          margin-bottom: 7px;
        }

        .ai-score-row strong {
          font-size: 22px;
        }

        .ai-score-row small {
          font-size: 12px;
          color: #94a3b8;
          margin-left: 3px;
        }

        .ai-section {
          margin-top: 18px;
          padding-top: 18px;
          border-top: 1px solid rgba(148, 163, 184, 0.14);
        }

        .ai-section h3 {
          margin: 0 0 13px;
          font-size: 16px;
        }

        .ai-detail-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
        }

        .ai-detail-grid p {
          margin: 0;
          padding: 12px 14px;
          border-radius: 12px;
          background: rgba(15, 23, 42, 0.38);
        }

        .ai-detail-grid strong {
          font-size: 14px;
        }

        .ai-action {
          margin-top: 20px;
          padding: 16px;
          border-left: 4px solid #38bdf8;
          border-radius: 12px;
          background: rgba(14, 165, 233, 0.09);
        }

        .ai-action span {
          font-size: 11px;
          letter-spacing: 1px;
          color: #67e8f9;
          font-weight: 800;
        }

        .ai-action p {
          margin: 7px 0 8px;
          line-height: 1.5;
        }

        .ai-action strong {
          font-size: 12px;
        }

        .modal-recommendations {
          display: grid;
          gap: 9px;
        }

        .modal-recommendations > div {
          display: flex;
          gap: 12px;
          align-items: flex-start;
          padding: 11px 12px;
          border-radius: 11px;
          background: rgba(15, 23, 42, 0.35);
        }

        .modal-recommendations b {
          display: grid;
          place-items: center;
          flex: 0 0 26px;
          height: 26px;
          border-radius: 8px;
          background: rgba(99, 102, 241, 0.32);
          font-size: 12px;
        }

        .modal-recommendations span {
          line-height: 1.45;
          font-size: 13px;
        }

        @media (max-width: 650px) {
          .ai-modal-overlay {
            padding: 10px;
          }

          .ai-modal {
            padding: 20px;
            border-radius: 16px;
            max-height: 94vh;
          }

          .ai-modal-head {
            display: block;
          }

          .risk-pill {
            display: inline-block;
            margin-top: 12px;
          }

          .ai-score-row {
            grid-template-columns: 1fr;
          }

          .ai-detail-grid {
            grid-template-columns: 1fr;
          }

          .ai-modal h2 {
            font-size: 23px;
          }
        }
      `}</style>

      <div className="app">

        {/* =====================================================
            SIDEBAR
        ====================================================== */}

        <aside className={`sidebar ${mobileNavOpen ? "open" : ""}`}>

          <div className="logo">
            <div className="logo-icon">
              <ShieldAlert size={25} />
            </div>

            <div>
              <h2>DisasterAI</h2>
              <span>COMMAND CENTER</span>
            </div>
          </div>

          <nav>
            <a href="#dashboard" className={activeSection === "dashboard" ? "active" : ""} onClick={() => openSection("dashboard")}>
              <ShieldAlert size={19} />
              Dashboard
            </a>

            <a href="#disaster-map" className={activeSection === "disaster-map" ? "active" : ""} onClick={() => openSection("disaster-map")}>
              <MapPin size={19} />
              Disaster Map
            </a>

            <a href="#sensors" className={activeSection === "sensors" ? "active" : ""} onClick={() => openSection("sensors")}>
              <Radio size={19} />
              Sensors
            </a>

            <a href="#cameras" className={activeSection === "cameras" ? "active" : ""} onClick={() => openSection("cameras")}>
              <Camera size={19} />
              Cameras
            </a>

            <a href="#rescue-teams" className={activeSection === "rescue-teams" ? "active" : ""} onClick={() => openSection("rescue-teams")}>
              <Users size={19} />
              Rescue Teams
            </a>

            <a href="#personnel-directory" className={activeSection === "personnel-directory" ? "active" : ""} onClick={() => openSection("personnel-directory")}>
              <ContactRound size={19} />
              Users &amp; Personnel
            </a>

            <a href="#alerts" className={activeSection === "alerts" ? "active" : ""} onClick={() => openSection("alerts")}>
              <Bell size={19} />
              Alerts
              <span className="nav-badge">
                {alertList.length}
              </span>
            </a>
          </nav>

          <div className="system-status">
            <div className="status-dot"></div>

            <div>
              <strong>
                {backendOnline
                  ? "System Online"
                  : "System Offline"}
              </strong>

              <small>
                {backendOnline
                  ? "Sensor API connected"
                  : "Waiting for FastAPI"}
              </small>
            </div>
          </div>

        </aside>

        {/* =====================================================
            MAIN CONTENT
        ====================================================== */}

        {mobileNavOpen && <button className="sidebar-backdrop" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}

        <main className={`main ${activeSection === "personnel-directory" ? "personnel-view" : ""}`} id="dashboard">

          {/* HEADER */}

          <header className="header">

            <button type="button" className="mobile-menu" aria-label="Open navigation" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen((open) => !open)}>
              <Menu size={23} />
            </button>

            <div>
              <h1>Disaster Command Center</h1>
              <p>
                Real-time disaster intelligence &amp;
                response system
              </p>
            </div>

            <div className="header-right">

              <div className="live-status">
                <span></span>
                {backendOnline
                  ? "LIVE"
                  : "OFFLINE"}
              </div>

              <button
                type="button"
                className="notification"
                onClick={() => { openSection("alerts"); document.getElementById("alerts")?.scrollIntoView({ behavior: "smooth" }); }}
              >
                <Bell size={20} />
                <span>{alertList.length}</span>
              </button>

              <div className="profile">
                <div className="avatar">
                  OP
                </div>

                <div>
                  <strong>{session?.user?.full_name || "Operator"}</strong>
                  <small>Control Room</small>
                </div>
              </div>

              <button type="button" className="operator-logout" onClick={onLogout} aria-label="Logout operator"><LogOut size={17} /></button>

            </div>
          </header>

          {/* ===================================================
              STATISTICS
          ==================================================== */}

          <section className="stats-grid">

            {stats.map((stat) => {
              const Icon = stat.icon;

              return (
                <div
                  className={`stat-card ${stat.type}`}
                  key={stat.title}
                >
                  <div className="stat-top">

                    <div>
                      <p>{stat.title}</p>

                      <div className="stat-value">
                        {stat.value}

                        {stat.unit && (
                          <span className="stat-unit">
                            {stat.unit}
                          </span>
                        )}
                      </div>

                      <small>
                        {stat.subtitle}
                      </small>
                    </div>

                    <div className="stat-icon">
                      <Icon size={23} />
                    </div>

                  </div>
                </div>
              );
            })}

          </section>

          {/* ===================================================
              MAP + ALERTS
          ==================================================== */}

          <section className="content-grid">

            <div className={`panel map-panel ${mapExpanded ? "expanded" : ""}`} id="disaster-map">

              <div className="panel-header">

                <div>
                  <h2>Live Disaster Map</h2>
                  <p>
                    Current situation overview
                  </p>
                </div>

                <button
                  type="button"
                  className="map-button"
                  onClick={() => setMapExpanded((expanded) => !expanded)}
                >
                  {mapExpanded ? "Close Full Map" : "Full Map"}
                </button>

              </div>

              <DisasterMap externalData={externalData} riskScore={fusedRiskScore} fieldReports={fieldReports} />

            </div>

            <div className="panel alerts-panel" id="alerts">

              <div className="panel-header">

                <div>
                  <h2>Active Alerts</h2>
                  <p>
                    Latest emergency events
                  </p>
                </div>

                <span className="alert-count">
                  {alertList.length}
                </span>

              </div>

              <div className="alerts-list">

                {alertList.length > 0 ? (
                  alertList.slice(0, showAllAlerts ? alertList.length : 4).map(
                    (alert, index) => (
                      <div
                        className="alert-item"
                        key={`${alert?.title ?? "alert"}-${index}`}
                      >
                        <div
                          className={`alert-icon ${
                            alert?.level ?? "warning"
                          }`}
                        >
                          <AlertTriangle size={18} />
                        </div>

                        <div className="alert-info">

                          <strong>
                            {alert?.title ??
                              "Emergency Alert"}
                          </strong>

                          <span>
                            <MapPin size={13} />
                            {alert?.location ??
                              "Unknown location"}
                            <b className="alert-language">{alert?.language || "English"}</b>
                          </span>

                        </div>

                        <small>
                          {alert?.time ?? "--"}
                        </small>
                      </div>
                    )
                  )
                ) : (
                  <div className="alert-item">
                    <div className="alert-info">
                      <strong>
                        No active alerts
                      </strong>

                      <span>
                        System is monitoring live conditions.
                      </span>
                    </div>
                  </div>
                )}

              </div>

              <button
                type="button"
                className="view-alerts"
                onClick={() => setShowAllAlerts((show) => !show)}
              >
                {showAllAlerts ? "Show latest alerts" : `View all ${alertList.length} alerts`}
              </button>

            </div>

          </section>

          {/* ===================================================
              LOWER GRID
          ==================================================== */}

          <section className="lower-grid">

            {/* SENSOR MONITORING */}

            <div className="panel sensor-panel" id="sensors">

              <div className="panel-header">

                <div>
                  <h2>Sensor Monitoring</h2>
                  <p>River Station 02</p>
                </div>

                <div className="sensor-online">

                  <span></span>

                  {backendOnline
                    ? "ONLINE"
                    : "OFFLINE"}

                </div>

              </div>

              {sensorError && (
                <p
                  role="alert"
                  className="sensor-error"
                >
                  {sensorError}
                </p>
              )}

              <div className="sensor-data">

                {liveSensors.map(
                  (sensor) => (
                    <div
                      key={sensor.label}
                    >
                      <span>
                        {sensor.label}
                      </span>

                      <strong>
                        {sensor.value}{" "}
                        <small>
                          {sensor.unit}
                        </small>
                      </strong>

                      <small>
                        {sensor.note}
                      </small>
                    </div>
                  )
                )}

              </div>

              <div
                className="sensor-metadata"
                aria-live="polite"
              >
                <p>
                  <strong>
                    Data source:
                  </strong>{" "}
                  {sensorData?.source ??
                    "--"}
                </p>

                <p>
                  <strong>
                    Last reading:
                  </strong>{" "}
                  {formatTimestamp(
                    sensorData?.timestamp
                  )}
                </p>
              </div>

              <SensorChart />

            </div>

            {/* AI RISK HISTORY */}

            <div className="panel risk-history-panel">

              <div className="panel-header">

                <div>
                  <h2>
                    AI Risk Evolution
                  </h2>

                  <p>
                    Latest AI decision history
                  </p>
                </div>

                <div className="ai-badge">
                  LIVE
                </div>

              </div>

              {riskHistory.length > 0 ? (
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-end",
                      gap: "6px",
                      height: "180px",
                      padding:
                        "20px 10px 10px",
                      borderBottom:
                        "1px solid #e5e7eb",
                    }}
                  >

                    {riskHistory.map(
                      (item, index) => {

                        const score = Number(
                          item?.risk_score ?? 0
                        );

                        const safeScore =
                          Number.isFinite(score)
                            ? Math.max(
                                5,
                                Math.min(
                                  100,
                                  score
                                )
                              )
                            : 5;

                        let background =
                          "#16a34a";

                        if (safeScore >= 80) {
                          background =
                            "#dc2626";
                        } else if (
                          safeScore >= 60
                        ) {
                          background =
                            "#f59e0b";
                        }

                        return (
                          <div
                            key={`${
                              item?.timestamp ??
                              "risk"
                            }-${index}`}
                            title={`${
                              item?.timestamp ??
                              ""
                            } — Risk ${
                              item?.risk_score ??
                              "--"
                            }`}
                            style={{
                              flex: 1,
                              height: `${safeScore}%`,
                              minHeight: "8px",
                              borderRadius:
                                "5px 5px 0 0",
                              background,
                            }}
                          />
                        );
                      }
                    )}

                  </div>

                  <p>
                    Current:{" "}
                    {latestRisk?.risk_score ??
                      "--"}
                    /100 —{" "}
                    {latestRisk?.risk_level ??
                      "--"}
                  </p>
                </>
              ) : (
                <div
                  style={{
                    padding: "30px",
                    textAlign: "center",
                  }}
                >
                  <p>
                    Collecting AI risk history...
                  </p>
                </div>
              )}

            </div>

            {/* AI RECOMMENDATIONS */}

            <div className="panel ai-panel">

              <div className="panel-header">

                <div>
                  <h2>
                    AI Recommendations
                  </h2>

                  <p>
                    Decision support engine
                  </p>
                </div>

                <div className="ai-badge">
                  AI
                </div>

              </div>

              <div className="recommendations">

                {displayedRecommendations.map(
                  (recommendation, index) => (
                    <div
                      className="recommendation"
                      key={`${recommendation}-${index}`}
                    >
                      <div className="recommendation-number">
                        {index + 1}
                      </div>

                      <p>
                        {recommendation}
                      </p>
                    </div>
                  )
                )}

              </div>

              <button
                type="button"
                className="analyze-button"
                onClick={runAIAnalysis}
                disabled={analyzing}
              >
                {analyzing
                  ? "Analyzing..."
                  : "Run AI Analysis"}
              </button>

            </div>

          </section>

          <section className="panel external-sources-panel" aria-labelledby="external-sources-title">
            <div className="panel-header external-sources-header">
              <div>
                <h2 id="external-sources-title">External Intelligence Network</h2>
                <p>Weather, terrain, seismic, river, satellite and official-alert data fused for landslide analysis</p>
              </div>
              <div className="source-summary" aria-live="polite">
                <span className={externalData ? "source-pulse online" : "source-pulse"}></span>
                {externalData ? `${externalData.available_sources?.length ?? 0} of 7 live` : "Connecting"}
              </div>
            </div>

            <div className="external-source-grid">
              {sourceCards.map((source) => {
                const response = externalSources[source.key];
                const isLive = response?.status === "success";
                const Icon = source.icon;
                return (
                  <button type="button" className={`external-source-card ${isLive ? "live" : "fallback"}`} key={source.key} onClick={() => setSelectedSourceKey(source.key)} aria-label={`Open ${source.label} details`}>
                    <div className="external-source-icon"><Icon size={19} /></div>
                    <div className="external-source-copy">
                      <div className="external-source-name"><strong>{source.label}</strong><span>{isLive ? "LIVE" : "FALLBACK"}</span></div>
                      <p>{source.value}</p>
                      <small>{isLive ? source.detail : response?.message ?? source.detail}</small>
                    </div>
                    <span className="source-open-hint">Tap to open →</span>
                  </button>
                );
              })}
            </div>

            <div className={`satellite-insight ${externalSources.satellite?.status === "success" ? "live" : "fallback"}`}>
              <div className="satellite-insight-title">
                <Satellite size={21} />
                <div>
                  <span>Satellite observation</span>
                  <strong>{satelliteCollection}</strong>
                </div>
              </div>
              <div>
                <span>Available scenes</span>
                <strong>{externalSources.satellite?.data?.count ?? 0}</strong>
              </div>
              <div>
                <span>Latest capture</span>
                <strong>{latestSatelliteScene?.acquired ? formatTimestamp(latestSatelliteScene.acquired) : "Not available"}</strong>
              </div>
              <div>
                <span>Cloud cover</span>
                <strong>{latestSatelliteScene?.cloud_cover != null ? `${formatNumber(latestSatelliteScene.cloud_cover, 1)}%` : "Not reported"}</strong>
              </div>
            </div>

            <div className="operational-usage">
              <div className="operational-usage-heading">
                <div>
                  <span>Operational data usage</span>
                  <strong>Every connected service has an active job</strong>
                </div>
                <small>LIVE INPUT → APP MODULE</small>
              </div>
              <div className="operational-usage-grid">
                {operationalUses.map(({ key, target, use, source }) => {
                  const Icon = source.icon;
                  const isLive = externalSources[key]?.status === "success";
                  return (
                    <article className="usage-row" key={key}>
                      <div className={`usage-status ${isLive ? "live" : "fallback"}`}><Icon size={16} /></div>
                      <div className="usage-source">
                        <strong>{source.label}</strong>
                        <span>{source.value}</span>
                      </div>
                      <div className="usage-arrow">→</div>
                      <div className="usage-target">
                        <strong>{target}</strong>
                        <span>{use}</span>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>

            <div className="fusion-strip">
              <div><span>Fusion location</span><strong>{externalData?.location ? `${formatNumber(externalData.location.latitude, 4)}, ${formatNumber(externalData.location.longitude, 4)}` : "Waiting for coordinates"}</strong></div>
              <div><span>Landslide rainfall input</span><strong>{formatNumber(externalData?.landslide_features?.rainfall_mm, 1)} mm</strong></div>
              <div><span>Official alerts</span><strong>{externalData?.landslide_features?.official_alert_count ?? 0}</strong></div>
              <div><span>River water-level input</span><strong>{externalData?.landslide_features?.water_level != null ? `${formatNumber(externalData.landslide_features.water_level, 2)} m` : "Waiting"}</strong></div>
            </div>
          </section>

          <FieldReports apiBaseUrl={API_BASE_URL} onReportsChange={setFieldReports} />

          <RescueTeams />

          <OperatorDirectory apiBaseUrl={API_BASE_URL} token={session?.token} />

          <OperatorApprovals apiBaseUrl={API_BASE_URL} token={session?.token} />

          <WarningCenter externalData={externalData} riskScore={fusedRiskScore} apiBaseUrl={API_BASE_URL} />

          {/* FOOTER */}

          <footer>
            <span>
              DisasterAI v1.0
            </span>

            <span>
              Last updated:{" "}
              {formatTimestamp(
                sensorData?.timestamp
              )}
            </span>

            <span>
              Data source:{" "}
              {sensorData?.source ??
                "Waiting"}
            </span>

            <span>
              External data: {externalData
                ? `${externalData.available_sources?.length ?? 0}/7 live`
                : "checking"}
            </span>
          </footer>

        </main>

        {selectedSource && (
          <div className="source-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="source-detail-title" onClick={() => setSelectedSourceKey(null)}>
            <div className="source-modal" onClick={(event) => event.stopPropagation()}>
              <button type="button" className="close-ai" aria-label="Close service details" onClick={() => setSelectedSourceKey(null)}>×</button>
              <span className="ai-modal-kicker">EXTERNAL INTELLIGENCE SERVICE</span>
              <div className="source-modal-title">
                {(() => { const SourceIcon = selectedSource.icon; return <SourceIcon size={25} />; })()}
                <div><h2 id="source-detail-title">{selectedSource.label}</h2><span className={selectedResponse?.status === "success" ? "source-state live" : "source-state fallback"}>{selectedResponse?.status === "success" ? "LIVE" : "FALLBACK"}</span></div>
              </div>
              <div className="source-detail-grid">
                <div><span>Current reading</span><strong>{selectedSource.value}</strong></div>
                <div><span>Last checked</span><strong>{formatTimestamp(selectedResponse?.timestamp)}</strong></div>
                <div><span>Used in</span><strong>{selectedUsage?.target}</strong></div>
                <div><span>Provider</span><strong>{selectedResponse?.source ?? selectedSource.label}</strong></div>
              </div>
              <div className="source-purpose"><strong>How this works in the app</strong><p>{selectedUsage?.use}</p></div>
              <div className="source-message"><strong>{selectedResponse?.status === "success" ? "Service response" : "Why fallback is showing"}</strong><p>{selectedResponse?.message ?? selectedSource.detail}</p></div>
              <button type="button" className="source-close-button" onClick={() => setSelectedSourceKey(null)}>Done</button>
            </div>
          </div>
        )}

        {/* =====================================================
            AI ANALYSIS MODAL
        ====================================================== */}

        {showAIAnalysis && (
          <div
            className="ai-modal-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ai-analysis-title"
          >
            <div className="ai-modal">

              <button
                type="button"
                className="close-ai"
                aria-label="Close AI analysis"
                onClick={() =>
                  setShowAIAnalysis(false)
                }
              >
                ×
              </button>

              <div className="ai-modal-head">

                <div>
                  <span className="ai-modal-kicker">
                    DISASTERAI DECISION SUPPORT
                  </span>

                  <h2 id="ai-analysis-title">
                    🤖 AI Disaster Analysis
                  </h2>
                </div>

                <span
                  className={`risk-pill ${
                    (
                      aiRisk?.risk_level ??
                      ""
                    ).toLowerCase()
                  }`}
                >
                  {aiRisk?.risk_level ??
                    "--"}
                </span>

              </div>

              {/* AI SCORE */}

              <div className="ai-score-row">

                <div>
                  <span>
                    Adaptive Risk
                  </span>

                  <strong>
                    {formatNumber(
                      aiRisk?.adaptive_risk_score,
                      2
                    )}

                    <small>
                      /100
                    </small>
                  </strong>
                </div>

                <div>
                  <span>
                    Flood Probability
                  </span>

                  <strong>
                    {formatNumber(
                      aiRisk?.flood_probability,
                      1
                    )}

                    <small>
                      %
                    </small>
                  </strong>
                </div>

                <div>
                  <span>
                    Priority
                  </span>

                  <strong>
                    {aiRisk?.response_priority ??
                      "--"}
                  </strong>
                </div>

              </div>

              {/* RISK INTELLIGENCE */}

              <section className="ai-section">

                <h3>
                  Risk Intelligence
                </h3>

                <div className="ai-detail-grid">

                  <p>
                    <span>
                      Risk trend
                    </span>

                    <strong>
                      {riskTrend?.trend ??
                        aiRisk?.risk_direction ??
                        "--"}
                    </strong>
                  </p>

                  <p>
                    <span>
                      Risk velocity
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.risk_velocity,
                        2
                      )}
                    </strong>
                  </p>

                  <p>
                    <span>
                      Risk acceleration
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.risk_acceleration,
                        2
                      )}
                    </strong>
                  </p>

                  <p>
                    <span>
                      Temporal state
                    </span>

                    <strong>
                      {aiRisk?.temporal_intelligence_state ??
                        "--"}
                    </strong>
                  </p>

                  <p>
                    <span>
                      Anomalies detected
                    </span>

                    <strong>
                      {aiRisk?.anomaly_count ??
                        "--"}
                    </strong>
                  </p>

                  <p>
                    <span>
                      Sensor reliability
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_reliability,
                        1
                      )}
                      %
                    </strong>
                  </p>

                </div>

              </section>

              {/* SENSOR SNAPSHOT */}

              <section className="ai-section">

                <h3>
                  Live Sensor Snapshot
                </h3>

                <div className="ai-detail-grid">

                  <p>
                    <span>
                      Water level
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.water_level ??
                          sensorData?.water_level,
                        2
                      )}{" "}
                      m
                    </strong>
                  </p>

                  <p>
                    <span>
                      Rainfall
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.rainfall ??
                          sensorData?.rainfall,
                        1
                      )}{" "}
                      mm
                    </strong>
                  </p>

                  <p>
                    <span>
                      Flow rate
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.flow_rate ??
                          sensorData?.flow_rate,
                        1
                      )}{" "}
                      m³/s
                    </strong>
                  </p>

                  <p>
                    <span>
                      Temperature
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.temperature ??
                          sensorData?.temperature,
                        1
                      )}{" "}
                      °C
                    </strong>
                  </p>

                  <p>
                    <span>
                      Humidity
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.humidity ??
                          sensorData?.humidity,
                        1
                      )}
                      %
                    </strong>
                  </p>

                  <p>
                    <span>
                      Wind speed
                    </span>

                    <strong>
                      {formatNumber(
                        aiRisk?.sensor_data
                          ?.wind_speed ??
                          sensorData?.wind_speed,
                        1
                      )}
                    </strong>
                  </p>

                </div>

              </section>

              {/* AI ACTION */}

              <section className="ai-action">

                <span>
                  RECOMMENDED ACTION
                </span>

                <p>
                  {aiRisk?.recommended_action ??
                    "Waiting for AI analysis..."}
                </p>

                <strong>
                  {aiRisk?.evacuation_required
                    ? "⚠ Evacuation required"
                    : "✓ No evacuation triggered by current model"}
                </strong>

              </section>

              {/* AI RECOMMENDATIONS */}

              <section className="ai-section">

                <h3>
                  AI Recommendations
                </h3>

                <div className="modal-recommendations">

                  {displayedRecommendations.map(
                    (
                      recommendation,
                      index
                    ) => (
                      <div
                        key={`${recommendation}-${index}`}
                      >
                        <b>
                          {index + 1}
                        </b>

                        <span>
                          {recommendation}
                        </span>
                      </div>
                    )
                  )}

                </div>

              </section>

            </div>
          </div>
        )}

      </div>
    </>
  );
}

export default App;
