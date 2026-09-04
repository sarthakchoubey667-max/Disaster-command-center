import { Activity, AlertTriangle, Flame, LogOut, MapPin, Navigation, Radio, ShieldAlert, Siren, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import DisasterMap from "./DisasterMap";
import FieldReports from "./FieldReports";
import WarningCenter from "./WarningCenter";
import "./App.css";
import "./Portal.css";

const roleContent = {
  citizen: { label: "Citizen Safety", icon: Users, subtitle: "Risk and emergency information for your area", cards: ["Current Area Risk", "Active Alerts", "Nearby Danger Zones", "Emergency Helpline"] },
  police: { label: "Police Operations", icon: ShieldAlert, subtitle: "Incident, road and public-safety coordination", cards: ["Active Incidents", "Critical Zones", "Road Blockages", "Missing Person Cases"] },
  fire: { label: "Fire Response", icon: Flame, subtitle: "Unit dispatch and safe-route recommendations", cards: ["Active Emergencies", "Units Available", "Safe Routes", "Blocked Roads"] },
  rescue: { label: "Rescue Operations", icon: Siren, subtitle: "Priority rescue requests and team coordination", cards: ["Active Emergencies", "Critical Zones", "Rescue Requests", "Team Status"] },
};

export default function RoleDashboard({ apiBaseUrl, session, onLogout }) {
  const [externalData, setExternalData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const content = roleContent[session.user.role] || roleContent.citizen;
  const RoleIcon = content.icon;
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [fusionResponse, alertResponse] = await Promise.all([fetch(`${apiBaseUrl}/api/data-fusion`, { cache: "no-store" }), fetch(`${apiBaseUrl}/api/alerts`, { cache: "no-store" })]);
        const fusion = await fusionResponse.json(); const alertData = await alertResponse.json();
        if (mounted) { setExternalData(fusion); setAlerts(alertData.alerts || alertData.data || []); }
      } catch { /* the last safe snapshot remains visible */ }
    };
    load(); const timer = setInterval(load, 30000); return () => { mounted = false; clearInterval(timer); };
  }, [apiBaseUrl]);
  const risk = Number(externalData?.operational?.risk?.score ?? 0);
  const reports = Number(externalData?.landslide_features?.field_report_count ?? 0);
  const criticalZones = risk >= 80 ? 3 : risk >= 60 ? 2 : risk >= 35 ? 1 : 0;
  const roadBlockages = alerts.filter((alert) => /road|blocked/i.test(alert.title || "")).length;
  const values = useMemo(() => session.user.role === "citizen" ? [`${risk.toFixed(0)}/100`, alerts.length, criticalZones, "112"] : session.user.role === "police" ? [alerts.length + reports, criticalZones, roadBlockages, 0] : session.user.role === "fire" ? [alerts.length, 2, Math.max(1, 3 - roadBlockages), roadBlockages] : [alerts.length, criticalZones, reports, "Available"], [alerts.length, criticalZones, reports, risk, roadBlockages, session.user.role]);

  return <main className="role-page">
    <header className="role-header"><div className="role-brand"><RoleIcon size={25} /><div><strong>{content.label}</strong><span>DisasterAI connected response network</span></div></div><div className="role-user"><div><strong>{session.user.full_name}</strong><span>{session.user.role} · {session.user.location}</span></div><button onClick={onLogout}><LogOut size={16} /> Logout</button></div></header>
    <section className="role-welcome"><div><span>VERIFIED {session.user.role.toUpperCase()} ACCESS</span><h1>{content.subtitle}</h1><p>Live intelligence shared from the DisasterAI Operator Command Center.</p></div><div className={`role-risk ${risk >= 60 ? "high" : ""}`}><Activity size={20} /><span>Current risk</span><strong>{risk.toFixed(1)}</strong></div></section>
    <section className="role-stat-grid">{content.cards.map((label, index) => <article key={label}><div className="role-stat-icon">{index === 0 ? <AlertTriangle size={20} /> : index === 1 ? <Radio size={20} /> : index === 2 ? <Navigation size={20} /> : <Users size={20} />}</div><span>{label}</span><strong>{values[index]}</strong><small>Live command-center data</small></article>)}</section>
    {session.user.role === "fire" && <section className="panel dispatch-panel"><div><span>RECOMMENDED UNIT</span><h2>Fire Unit 03</h2><p><MapPin size={13} /> 4.2 km away · ETA 11 minutes</p></div><div><span>SAFE ROUTE</span><h2>Route B</h2><p>17 km · 30 min · Low landslide risk</p></div><button>View live route</button></section>}
    <section className="role-content-grid"><div className="panel"><div className="panel-header"><div><h2>Live Disaster Map</h2><p>Shared risk zones, roads and field incidents</p></div></div><DisasterMap externalData={externalData} fieldReports={[]} /></div><div className="panel role-alerts"><div className="panel-header"><div><h2>Priority Alerts</h2><p>Official warnings for your response area</p></div></div>{alerts.slice(0, 5).map((alert, index) => <article key={alert.id || index}><AlertTriangle size={17} /><div><strong>{alert.title || alert.headline || "Official warning"}</strong><span>{alert.area || alert.location || "North Eastern Region"}</span></div></article>)}{!alerts.length && <p className="role-empty">Waiting for current official alerts.</p>}</div></section>
    <FieldReports apiBaseUrl={apiBaseUrl} onReportsChange={() => {}} />
    <WarningCenter externalData={externalData} riskScore={risk} apiBaseUrl={apiBaseUrl} />
  </main>;
}
