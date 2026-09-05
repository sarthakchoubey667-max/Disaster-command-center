import { Building2, Flame, Mail, MapPin, Phone, Search, ShieldAlert, Siren, UserRound, UsersRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const roleMeta = {
  citizen: { label: "Citizen / User", icon: UserRound },
  police: { label: "Police", icon: ShieldAlert },
  fire: { label: "Fire", icon: Flame },
  rescue: { label: "Rescue / Ambulance", icon: Siren },
  hospital: { label: "Hospital", icon: Building2 },
};

export default function OperatorDirectory({ apiBaseUrl, token }) {
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("Loading connected departments…");
  const load = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/operator/department-directory`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Directory unavailable");
      setUsers(data.users || []);
      setMessage("");
    } catch (error) { setMessage(error.message); }
  }, [apiBaseUrl, token]);
  useEffect(() => { load(); const timer = setInterval(load, 5000); return () => clearInterval(timer); }, [load]);
  const visible = useMemo(() => users.filter((user) => JSON.stringify(user).toLowerCase().includes(query.toLowerCase())), [query, users]);
  const counts = useMemo(() => Object.keys(roleMeta).map((role) => ({ role, count: users.filter((user) => user.role === role).length })), [users]);

  return <section className="panel personnel-directory" id="personnel-directory">
    <div className="panel-header directory-header"><div><h2>Connected Users &amp; Departments</h2><p>Verified citizens, Police, Fire, Rescue and Hospital network</p></div><label><Search size={14}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, department or area"/></label></div>
    <div className="directory-summary">{counts.map(({ role, count }) => { const MetaIcon = roleMeta[role].icon; return <div key={role}><MetaIcon size={16}/><span>{roleMeta[role].label}</span><strong>{count}</strong></div>; })}</div>
    <div className="directory-grid">{visible.map((user) => { const meta = roleMeta[user.role]; const RoleIcon = meta.icon; const details = user.official_details || {}; return <article key={user.id} className={`directory-card ${user.role}`}><div className="directory-role"><span><RoleIcon size={18}/></span><div><b>{meta.label}</b><small className={user.status}>{user.status.replace("_", " ")}</small></div></div><h3>{user.full_name}</h3><p>{details.designation || details.hospital_type || "Verified personnel"}</p><dl><div><dt>Department</dt><dd>{details.department || details.hospital_id || "Not provided"}</dd></div><div><dt>Unit / Zone</dt><dd>{details.unit || details.duty_area || user.location || "Not provided"}</dd></div></dl><div className="directory-contact"><span><Phone size={12}/>{user.mobile || details.emergency_contact || "Not provided"}</span><span><Mail size={12}/>{user.email}</span><span><MapPin size={12}/>{user.location || details.full_address || "Not provided"}</span></div></article>; })}</div>
    {!visible.length && <p className="directory-empty"><UsersRound size={20}/>{message || "No matching verified user found."}</p>}
  </section>;
}
