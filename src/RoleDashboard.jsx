import { Activity, AlertTriangle, Ambulance, BedDouble, Building2, Droplets, Flame, LogOut, MapPin, Navigation, Radio, Save, ShieldAlert, Siren, Users } from "lucide-react";
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
  hospital: { label: "Hospital Emergency Desk", icon: Building2, subtitle: "Live capacity, casualty and ambulance coordination", cards: ["Beds Available", "ICU Available", "Incoming Cases", "Ambulances"] },
};

function HospitalPanel({ apiBaseUrl, session, onData }) {
  const [data, setData] = useState(null); const [message, setMessage] = useState("");
  useEffect(() => { fetch(`${apiBaseUrl}/api/hospital/status`, { headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store" }).then((r) => r.json()).then((r) => { setData(r.data); onData(r.data); }).catch(() => setMessage("Hospital resource service unavailable")); }, [apiBaseUrl, session.token, onData]);
  if (!data) return <section className="panel hospital-panel"><p className="role-empty">{message || "Loading hospital resources…"}</p></section>;
  const update = (key, value) => setData((current) => ({ ...current, [key]: value }));
  const save = async () => { const response = await fetch(`${apiBaseUrl}/api/hospital/status`, { method: "PUT", headers: { Authorization: `Bearer ${session.token}`, "Content-Type": "application/json" }, body: JSON.stringify(data) }); const result = await response.json(); if (response.ok) { setData(result.data); onData(result.data); setMessage("Live resource status shared with command center"); } else setMessage(result.detail || "Update failed"); };
  return <section className="panel hospital-panel"><div className="panel-header"><div><h2>Live Hospital Resources</h2><p>Update beds, ICU, oxygen and incoming casualty load</p></div><button className="resource-save" onClick={save}><Save size={14} /> Share live status</button></div><div className="resource-grid">{[["beds_available","Beds available",BedDouble],["icu_available","ICU available",Activity],["emergency_beds","Emergency beds",Siren],["ambulances_available","Ambulances",Ambulance],["oxygen_units","Oxygen units",Activity],["incoming_cases","Incoming cases",Users],["casualties_admitted","Casualties admitted",Users]].map(([key,label,Icon]) => <label key={key}><Icon size={17}/><span>{label}</span><input type="number" min="0" value={data[key]} onChange={(e) => update(key, Number(e.target.value))}/></label>)}<label><Droplets size={17}/><span>Blood bank</span><select value={data.blood_bank_available ? "1" : "0"} onChange={(e) => update("blood_bank_available", e.target.value === "1")}><option value="1">Available</option><option value="0">Unavailable</option></select></label><label className="resource-note"><AlertTriangle size={17}/><span>Resource shortage</span><input value={data.shortage_note} onChange={(e) => update("shortage_note", e.target.value)} placeholder="e.g. O-negative blood required"/></label></div>{message && <p className="approval-message">{message}</p>}</section>;
}

function RescueFieldPanel({ apiBaseUrl, session }) {
  const [form, setForm] = useState({ vehicle_number: "", vehicle_type: "BLS", team_members: [], equipment_status: "Ready", blockage_status: "Clear", critical_count: 0, serious_count: 0, minor_count: 0, destination_hospital: "Nearest safe hospital" }); const [message, setMessage] = useState("");
  const update = (e) => setForm((current) => ({ ...current, [e.target.name]: e.target.type === "number" ? Number(e.target.value) : e.target.value }));
  const submit = async (e) => { e.preventDefault(); const response = await fetch(`${apiBaseUrl}/api/rescue/field-update`, { method: "POST", headers: { Authorization: `Bearer ${session.token}`, "Content-Type": "application/json" }, body: JSON.stringify(form) }); setMessage(response.ok ? "Field update shared with hospital and command center" : "Update could not be shared"); };
  return <section className="panel rescue-field-panel"><div className="panel-header"><div><h2>Ambulance Quick Field Update</h2><p>Vehicle, route blockage, triage and destination hospital</p></div></div><form onSubmit={submit}><label>Vehicle number<input name="vehicle_number" value={form.vehicle_number} onChange={update} required/></label><label>Vehicle type<select name="vehicle_type" value={form.vehicle_type} onChange={update}><option>BLS</option><option>ALS</option></select></label><label>Equipment status<input name="equipment_status" value={form.equipment_status} onChange={update}/></label><label>Road status<select name="blockage_status" value={form.blockage_status} onChange={update}><option>Clear</option><option>Partially blocked</option><option>Blocked</option></select></label><label>Critical (Red)<input type="number" min="0" name="critical_count" value={form.critical_count} onChange={update}/></label><label>Serious (Yellow)<input type="number" min="0" name="serious_count" value={form.serious_count} onChange={update}/></label><label>Minor (Green)<input type="number" min="0" name="minor_count" value={form.minor_count} onChange={update}/></label><label>Destination hospital<input name="destination_hospital" value={form.destination_hospital} onChange={update}/></label><button><Ambulance size={15}/> Share rescue update</button></form>{message && <p className="approval-message">{message}</p>}</section>;
}

export default function RoleDashboard({ apiBaseUrl, session, onLogout }) {
  const [externalData, setExternalData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [hospitalData, setHospitalData] = useState(null);
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
  const values = useMemo(() => session.user.role === "citizen" ? [`${risk.toFixed(0)}/100`, alerts.length, criticalZones, "112"] : session.user.role === "police" ? [alerts.length + reports, criticalZones, roadBlockages, 0] : session.user.role === "fire" ? [alerts.length, 2, Math.max(1, 3 - roadBlockages), roadBlockages] : session.user.role === "hospital" ? [hospitalData?.beds_available ?? "--", hospitalData?.icu_available ?? "--", hospitalData?.incoming_cases ?? 0, hospitalData?.ambulances_available ?? "--"] : [alerts.length, criticalZones, reports, "Available"], [alerts.length, criticalZones, hospitalData, reports, risk, roadBlockages, session.user.role]);

  return <main className="role-page">
    <header className="role-header"><div className="role-brand"><RoleIcon size={25} /><div><strong>{content.label}</strong><span>DisasterAI connected response network</span></div></div><div className="role-user"><div><strong>{session.user.full_name}</strong><span>{session.user.role} · {session.user.location}</span></div><button onClick={onLogout}><LogOut size={16} /> Logout</button></div></header>
    <section className="role-welcome"><div><span>VERIFIED {session.user.role.toUpperCase()} ACCESS</span><h1>{content.subtitle}</h1><p>Live intelligence shared from the DisasterAI Operator Command Center.</p></div><div className={`role-risk ${risk >= 60 ? "high" : ""}`}><Activity size={20} /><span>Current risk</span><strong>{risk.toFixed(1)}</strong></div></section>
    <section className="role-stat-grid">{content.cards.map((label, index) => <article key={label}><div className="role-stat-icon">{index === 0 ? <AlertTriangle size={20} /> : index === 1 ? <Radio size={20} /> : index === 2 ? <Navigation size={20} /> : <Users size={20} />}</div><span>{label}</span><strong>{values[index]}</strong><small>Live command-center data</small></article>)}</section>
    {session.user.role === "fire" && <section className="panel dispatch-panel"><div><span>RECOMMENDED UNIT</span><h2>Fire Unit 03</h2><p><MapPin size={13} /> 4.2 km away · ETA 11 minutes</p></div><div><span>SAFE ROUTE</span><h2>Route B</h2><p>17 km · 30 min · Low landslide risk</p></div><button>View live route</button></section>}
    {session.user.role === "hospital" && <HospitalPanel apiBaseUrl={apiBaseUrl} session={session} onData={setHospitalData} />}
    {session.user.role === "rescue" && <RescueFieldPanel apiBaseUrl={apiBaseUrl} session={session} />}
    <section className="role-content-grid"><div className="panel"><div className="panel-header"><div><h2>Live Disaster Map</h2><p>Shared risk zones, roads and field incidents</p></div></div><DisasterMap externalData={externalData} fieldReports={[]} /></div><div className="panel role-alerts"><div className="panel-header"><div><h2>Priority Alerts</h2><p>Official warnings for your response area</p></div></div>{alerts.slice(0, 5).map((alert, index) => <article key={alert.id || index}><AlertTriangle size={17} /><div><strong>{alert.title || alert.headline || "Official warning"}</strong><span>{alert.area || alert.location || "North Eastern Region"}</span></div></article>)}{!alerts.length && <p className="role-empty">Waiting for current official alerts.</p>}</div></section>
    <FieldReports apiBaseUrl={apiBaseUrl} onReportsChange={() => {}} />
    <WarningCenter externalData={externalData} riskScore={risk} apiBaseUrl={apiBaseUrl} />
  </main>;
}
