import { Activity, ArrowRight, Flame, LockKeyhole, ShieldAlert, Siren, UserRound } from "lucide-react";
import { useState } from "react";
import "./Portal.css";

const roles = [
  { value: "citizen", label: "Citizen / Local User", icon: UserRound },
  { value: "police", label: "Police Department", icon: ShieldAlert },
  { value: "fire", label: "Fire Department", icon: Flame },
  { value: "rescue", label: "Rescue Team", icon: Siren },
];

export default function AuthScreen({ apiBaseUrl, onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ role: "citizen", full_name: "", email: "", mobile: "", password: "", location: "", department: "", designation: "", unit: "", duty_area: "", code: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  const selectedRole = roles.find((role) => role.value === form.role);

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : mode === "verify" ? "/api/auth/verify-email" : "/api/auth/register";
      const payload = mode === "login" ? { email: form.email, password: form.password } : mode === "verify" ? { email: form.email, code: form.code } : { full_name: form.full_name, email: form.email, mobile: form.mobile, password: form.password, role: form.role, location: form.location, official_details: { department: form.department, designation: form.designation, unit: form.unit, duty_area: form.duty_area } };
      const response = await fetch(`${apiBaseUrl}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      if (mode === "login") onLogin(data);
      else if (mode === "register") { setMode("verify"); setMessage(data.email_delivery === "sent" ? "Verification code sent to your email." : "Email delivery is not configured yet. Contact the operator."); }
      else { setMode("login"); setMessage(data.account_status === "active" ? "Verified. You can login now." : "Verified. Your official account is waiting for operator approval."); }
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  };

  return <main className="auth-page">
    <section className="auth-hero"><div className="auth-brand"><ShieldAlert size={27} /><strong>DisasterAI</strong></div><div><span className="auth-kicker">NORTH EASTERN REGION</span><h1>Early warning.<br />Faster response.<br /><em>Safer communities.</em></h1><p>One connected platform for citizens, field responders and disaster-management authorities.</p></div><div className="auth-live"><Activity size={17} /><div><strong>Monitoring network online</strong><span>Weather · Terrain · River · Official alerts</span></div></div></section>
    <section className="auth-card">
      <div className="auth-card-head"><LockKeyhole size={22} /><div><h2>{mode === "login" ? "Secure login" : mode === "verify" ? "Verify your email" : "Create your account"}</h2><p>{mode === "login" ? "Access your role-specific dashboard" : mode === "verify" ? `Enter the 6-digit code sent to ${form.email}` : "Select your role and provide verified details"}</p></div></div>
      {mode === "register" && <div className="role-picker">{roles.map(({ value, label, icon: Icon }) => <button key={value} type="button" className={form.role === value ? "selected" : ""} onClick={() => setForm((current) => ({ ...current, role: value }))}><Icon size={18} /><span>{label}</span></button>)}</div>}
      <form onSubmit={submit}>
        {mode === "register" && <><label>Full name<input name="full_name" value={form.full_name} onChange={update} required /></label><label>Mobile number<input name="mobile" value={form.mobile} onChange={update} required /></label><label className="wide">Location / District<input name="location" value={form.location} onChange={update} required /></label></>}
        {mode !== "verify" && <><label className="wide">Email address<input name="email" type="email" value={form.email} onChange={update} required /></label><label className="wide">Password<input name="password" type="password" value={form.password} onChange={update} minLength="8" required /></label></>}
        {mode === "register" && form.role !== "citizen" && <div className="official-fields"><span>{selectedRole?.label} official details</span><label>Department / Station<input name="department" value={form.department} onChange={update} required /></label><label>Rank / Designation<input name="designation" value={form.designation} onChange={update} required /></label><label>Unit / Zone<input name="unit" value={form.unit} onChange={update} required /></label><label>Duty area<input name="duty_area" value={form.duty_area} onChange={update} required /></label></div>}
        {mode === "verify" && <label className="wide verification-code">6-digit verification code<input name="code" inputMode="numeric" maxLength="6" value={form.code} onChange={update} required /></label>}
        {message && <p className="auth-message">{message}</p>}
        <button className="auth-submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Login securely" : mode === "verify" ? "Verify account" : "Create & verify account"}<ArrowRight size={17} /></button>
      </form>
      <button className="auth-switch" type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setMessage(""); }}>{mode === "login" ? "New user? Create an account" : "Already registered? Login"}</button>
      <p className="operator-note">Operator access is private and cannot be requested from this page.</p>
    </section>
  </main>;
}
