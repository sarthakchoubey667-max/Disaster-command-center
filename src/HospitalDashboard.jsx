import { Activity, AlertTriangle, Ambulance, BedDouble, Building2, Droplets, LogOut, Save, Siren, Users } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import DisasterMap from "./DisasterMap";
import "./App.css";
import "./Portal.css";

const resourceFields = [
  ["beds_available", "Beds available", BedDouble], ["icu_available", "ICU available", Activity],
  ["emergency_beds", "Emergency beds", Siren], ["ambulances_available", "Ambulances", Ambulance],
  ["oxygen_units", "Oxygen units", Activity], ["incoming_cases", "Incoming cases", Users],
  ["casualties_admitted", "Casualties admitted", Users],
];

export default function HospitalDashboard({ apiBaseUrl, session, onLogout }) {
  const [resources, setResources] = useState(null);
  const [rescueUpdates, setRescueUpdates] = useState([]);
  const [externalData, setExternalData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [message, setMessage] = useState("");
  const headers = useMemo(() => ({ Authorization: `Bearer ${session.token}` }), [session.token]);

  const load = useCallback(async () => {
    try {
      const [statusResponse, rescueResponse, fusionResponse, alertResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/hospital/status`, { headers, cache: "no-store" }),
        fetch(`${apiBaseUrl}/api/operations/rescue-updates`, { headers, cache: "no-store" }),
        fetch(`${apiBaseUrl}/api/data-fusion`, { cache: "no-store" }),
        fetch(`${apiBaseUrl}/api/alerts`, { cache: "no-store" }),
      ]);
      if (!statusResponse.ok || !rescueResponse.ok) throw new Error("Hospital service unavailable");
      const [status, rescue, fusion, alertData] = await Promise.all([statusResponse.json(), rescueResponse.json(), fusionResponse.json(), alertResponse.json()]);
      setResources(status.data); setRescueUpdates(rescue.updates || []); setExternalData(fusion); setAlerts(alertData.alerts || alertData.data || []); setMessage("");
    } catch (error) { setMessage(error.message); }
  }, [apiBaseUrl, headers]);

  useEffect(() => { load(); const timer = setInterval(load, 30000); return () => clearInterval(timer); }, [load]);
  const update = (key, value) => setResources((current) => ({ ...current, [key]: value }));
  const save = async () => {
    const response = await fetch(`${apiBaseUrl}/api/hospital/status`, { method: "PUT", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(resources) });
    const result = await response.json();
    if (response.ok) { setResources(result.data); setMessage("Hospital status shared with rescue teams and command center"); } else setMessage(result.detail || "Update failed");
  };
  const risk = Number(externalData?.operational?.risk?.score ?? 0);

  return <main className="role-page hospital-page">
    <header className="role-header"><div className="role-brand"><Building2 size={25}/><div><strong>DisasterAI Hospital Network</strong><span>Independent emergency and casualty dashboard</span></div></div><div className="role-user"><div><strong>{session.user.full_name}</strong><span>Verified hospital · {session.user.location}</span></div><button onClick={onLogout}><LogOut size={16}/> Logout</button></div></header>
    <section className="role-welcome hospital-welcome"><div><span>VERIFIED HOSPITAL ACCESS</span><h1>Hospital Emergency Control</h1><p>Manage capacity, incoming casualties, ambulances and disaster access routes.</p></div><div className={`role-risk ${risk >= 60 ? "high" : ""}`}><Activity size={20}/><span>Nearby risk</span><strong>{risk.toFixed(1)}</strong></div></section>
    <section className="role-stat-grid"><article><div className="role-stat-icon"><BedDouble/></div><span>Beds available</span><strong>{resources?.beds_available ?? "--"}</strong><small>Live shared capacity</small></article><article><div className="role-stat-icon"><Activity/></div><span>ICU available</span><strong>{resources?.icu_available ?? "--"}</strong><small>Critical-care capacity</small></article><article><div className="role-stat-icon"><Ambulance/></div><span>Incoming rescues</span><strong>{rescueUpdates.length}</strong><small>Ambulances en route</small></article><article><div className="role-stat-icon"><AlertTriangle/></div><span>Official alerts</span><strong>{alerts.length}</strong><small>Nearby warnings</small></article></section>
    {resources && <section className="panel hospital-panel"><div className="panel-header"><div><h2>Hospital Resource Control</h2><p>Single-tap live capacity updates</p></div><button className="resource-save" onClick={save}><Save size={14}/> Share live status</button></div><div className="resource-grid">{resourceFields.map(([key,label,Icon]) => <label key={key}><Icon size={17}/><span>{label}</span><input type="number" min="0" value={resources[key]} onChange={(e) => update(key, Number(e.target.value))}/></label>)}<label><Droplets size={17}/><span>Blood bank</span><select value={resources.blood_bank_available ? "1" : "0"} onChange={(e) => update("blood_bank_available", e.target.value === "1")}><option value="1">Available</option><option value="0">Unavailable</option></select></label><label className="resource-note"><AlertTriangle size={17}/><span>Resource shortage</span><input value={resources.shortage_note} onChange={(e) => update("shortage_note", e.target.value)} placeholder="Blood, oxygen or medicine shortage"/></label></div></section>}
    <section className="hospital-operations-grid"><div className="panel"><div className="panel-header"><div><h2>Hospital Access Map</h2><p>Risk zones, roads and hospital approach routes</p></div></div><DisasterMap externalData={externalData} fieldReports={[]}/></div><div className="panel incoming-rescues"><div className="panel-header"><div><h2>Incoming Ambulances</h2><p>Live rescue-team triage feed</p></div></div>{rescueUpdates.slice(0,6).map((item) => <article key={item.id}><Ambulance size={18}/><div><strong>{item.vehicle_number || "Rescue vehicle"} · {item.vehicle_type}</strong><span>{item.destination_hospital || "Destination pending"}</span><small><b className="triage-red">{item.critical_count} critical</b> · {item.serious_count} serious · {item.minor_count} minor · Road: {item.blockage_status}</small></div></article>)}{!rescueUpdates.length && <p className="role-empty">No ambulances are currently en route.</p>}</div></section>
    {message && <p className="hospital-status-message">{message}</p>}
  </main>;
}
