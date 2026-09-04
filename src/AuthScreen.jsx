import { Activity, ArrowRight, Building2, Flame, LockKeyhole, ShieldAlert, Siren, UserRound } from "lucide-react";
import { useState } from "react";
import "./Portal.css";

const roles = [
  { value: "citizen", label: "Citizen", icon: UserRound }, { value: "police", label: "Police", icon: ShieldAlert },
  { value: "fire", label: "Fire", icon: Flame }, { value: "rescue", label: "Rescue / Ambulance", icon: Siren },
  { value: "hospital", label: "Hospital", icon: Building2 },
  { value: "operator", label: "Private Operator", icon: LockKeyhole },
];

export default function AuthScreen({ apiBaseUrl, onLogin }) {
  const [mode, setMode] = useState("login");
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [form, setForm] = useState({ role: "citizen", full_name: "", email: "", mobile: "", password: "", location: "", department: "", designation: "", unit: "", duty_area: "", code: "", hospital_type: "Government", latitude: "", longitude: "", emergency_contact: "", beds_total: "50", icu_total: "10", emergency_beds: "6", ambulances: "3", blood_bank: "Yes" });
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const update = (e) => setForm((current) => ({ ...current, [e.target.name]: e.target.value }));
  const selectedRole = roles.find((role) => role.value === form.role);
  const request = async (endpoint, payload) => { const response = await fetch(`${apiBaseUrl}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const data = await response.json(); if (!response.ok) throw new Error(data.detail || "Request failed"); return data; };

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      if (mode === "login") { onLogin(await request("/api/auth/login", { email: form.email, password: form.password, role: form.role })); return; }
      if (mode === "verify") { const data = await request("/api/auth/verify-email", { email: form.email, role: form.role, code: form.code }); setMode("login"); setMessage(data.account_status === "active" ? "Verified. You can login now." : "Verified. Waiting for operator approval."); return; }
      const hospital = form.role === "hospital";
      const official_details = hospital ? { hospital_id: form.department, hospital_type: form.hospital_type, full_address: form.location, latitude: form.latitude, longitude: form.longitude, emergency_contact: form.emergency_contact, bed_capacity: form.beds_total, icu_beds: form.icu_total, emergency_beds: form.emergency_beds, ambulances: form.ambulances, blood_bank: form.blood_bank } : { department: form.department, designation: form.designation, unit: form.unit, duty_area: form.duty_area };
      const data = await request("/api/auth/register", { full_name: form.full_name, email: form.email, mobile: form.mobile, password: form.password, role: form.role, location: form.location, official_details });
      setRegisteredEmail(form.email); setMode("verify"); setMessage(data.email_delivery === "sent" ? "Verification code sent." : "Email delivery is not configured. Contact operator.");
    } catch (error) { setMessage(error.message); } finally { setBusy(false); }
  };
  const resend = async () => { setBusy(true); try { const data = await request("/api/auth/resend-code", { email: form.email, role: form.role }); setMessage(data.email_delivery === "sent" ? "New code sent." : "Email service is not configured."); } catch (error) { setMessage(error.message); } finally { setBusy(false); } };
  const changeEmail = async () => { if (form.email === registeredEmail) { setMessage("Enter the corrected email first."); return; } setBusy(true); try { const data = await request("/api/auth/change-verification-email", { old_email: registeredEmail, new_email: form.email, role: form.role }); setRegisteredEmail(form.email); setMessage(data.email_delivery === "sent" ? "Email corrected and new code sent." : "Email corrected. Contact operator for verification."); } catch (error) { setMessage(error.message); } finally { setBusy(false); } };

  return <main className="auth-page">
    <section className="auth-hero"><div className="auth-brand"><ShieldAlert size={27} /><strong>DisasterAI</strong></div><div><span className="auth-kicker">CONNECTED RESPONSE NETWORK</span><h1>Early warning.<br />Faster response.<br /><em>Safer communities.</em></h1><p>Citizens, hospitals, rescue teams and authorities on one verified platform.</p></div><div className="auth-live"><Activity size={17} /><div><strong>Monitoring network online</strong><span>Weather · Terrain · Hospitals · Official alerts</span></div></div></section>
    <section className="auth-card">
      <div className="auth-card-head"><LockKeyhole size={22} /><div><h2>{mode === "login" ? "Secure login" : mode === "verify" ? "Verify your email" : "Create your account"}</h2><p>{mode === "verify" ? "Correct the email below if it was entered incorrectly" : "Choose the department you want to access"}</p></div></div>
      {mode !== "verify" && <div className="role-picker">{roles.filter((role) => mode === "login" || role.value !== "operator").map(({ value, label, icon: Icon }) => <button key={value} type="button" className={form.role === value ? "selected" : ""} onClick={() => setForm((current) => ({ ...current, role: value }))}><Icon size={18} /><span>{label}</span></button>)}</div>}
      <form onSubmit={submit}>
        {mode === "register" && <><label>{form.role === "hospital" ? "Hospital name" : "Full name"}<input name="full_name" value={form.full_name} onChange={update} required /></label><label>Mobile number<input name="mobile" value={form.mobile} onChange={update} required /></label><label className="wide">Full address / District<input name="location" value={form.location} onChange={update} required /></label></>}
        <label className="wide">Email address<input name="email" type="email" value={form.email} onChange={update} required /></label>
        {mode !== "verify" && <label className="wide">Password<input name="password" type="password" value={form.password} onChange={update} minLength="8" required /></label>}
        {mode === "register" && form.role !== "citizen" && form.role !== "hospital" && <div className="official-fields"><span>{selectedRole?.label} official details</span><label>Department / Station<input name="department" value={form.department} onChange={update} required /></label><label>Rank / Designation<input name="designation" value={form.designation} onChange={update} required /></label><label>Unit / Zone<input name="unit" value={form.unit} onChange={update} required /></label><label>Duty area<input name="duty_area" value={form.duty_area} onChange={update} required /></label></div>}
        {mode === "register" && form.role === "hospital" && <div className="official-fields"><span>Hospital verification & capacity</span><label>Hospital registration ID<input name="department" value={form.department} onChange={update} required /></label><label>Hospital type<select name="hospital_type" value={form.hospital_type} onChange={update}><option>Government</option><option>Private</option></select></label><label>Latitude<input name="latitude" value={form.latitude} onChange={update} /></label><label>Longitude<input name="longitude" value={form.longitude} onChange={update} /></label><label>Emergency contact<input name="emergency_contact" value={form.emergency_contact} onChange={update} required /></label><label>Bed capacity<input name="beds_total" type="number" value={form.beds_total} onChange={update} /></label><label>ICU beds<input name="icu_total" type="number" value={form.icu_total} onChange={update} /></label><label>Emergency beds<input name="emergency_beds" type="number" value={form.emergency_beds} onChange={update} /></label><label>Ambulances<input name="ambulances" type="number" value={form.ambulances} onChange={update} /></label><label>Blood bank<select name="blood_bank" value={form.blood_bank} onChange={update}><option>Yes</option><option>No</option></select></label></div>}
        {mode === "verify" && <><label className="wide verification-code">6-digit verification code<input name="code" inputMode="numeric" maxLength="6" value={form.code} onChange={update} required /></label><div className="verification-actions"><button type="button" onClick={changeEmail} disabled={busy}>Wrong email? Update & resend</button><button type="button" onClick={resend} disabled={busy}>Resend code</button></div></>}
        {message && <p className="auth-message">{message}</p>}<button className="auth-submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Login to selected department" : mode === "verify" ? "Verify account" : "Create & verify account"}<ArrowRight size={17} /></button>
      </form>
      <button className="auth-switch" type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setMessage(""); }}>{mode === "login" ? "New user? Create an account" : "Already registered? Login"}</button>
      <p className="operator-note">One email can have separate verified accounts for different departments.</p>
    </section>
  </main>;
}
