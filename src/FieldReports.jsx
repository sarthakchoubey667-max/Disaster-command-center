import { Camera, MapPin, Send, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const initialForm = {
  report_type: "crack", severity: "moderate", description: "",
  latitude: "26.1445", longitude: "91.7362", reporter_name: "",
  road_status: "unknown",
};
const QUEUE_KEY = "disaster-ai-pending-field-reports";

export default function FieldReports({ apiBaseUrl, onReportsChange }) {
  const [reports, setReports] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [media, setMedia] = useState(null);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [queuedCount, setQueuedCount] = useState(() => JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]").length);

  const loadReports = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/field-reports?limit=20`, { cache: "no-store" });
      if (!response.ok) throw new Error("Reports unavailable");
      const data = await response.json();
      const items = data.reports ?? [];
      setReports(items);
      onReportsChange?.(items);
    } catch {
      setMessage("Field-report service is reconnecting.");
    }
  }, [apiBaseUrl, onReportsChange]);

  useEffect(() => { loadReports(); }, [loadReports]);

  useEffect(() => {
    const syncQueued = async () => {
      const queued = JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
      if (!queued.length) return;
      const remaining = [];
      for (const report of queued) {
        try {
          const body = new FormData();
          Object.entries(report).forEach(([key, value]) => body.append(key, value));
          const response = await fetch(`${apiBaseUrl}/api/field-reports`, { method: "POST", body });
          if (!response.ok) remaining.push(report);
        } catch { remaining.push(report); }
      }
      localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
      setQueuedCount(remaining.length);
      if (!remaining.length) { setMessage("Offline reports synchronized."); loadReports(); }
    };
    window.addEventListener("online", syncQueued);
    if (navigator.onLine) syncQueued();
    return () => window.removeEventListener("online", syncQueued);
  }, [apiBaseUrl, loadReports]);

  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  const useLocation = () => {
    if (!navigator.geolocation) return setMessage("Location is not supported on this device.");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setForm((current) => ({ ...current, latitude: coords.latitude.toFixed(6), longitude: coords.longitude.toFixed(6) })),
      () => setMessage("Location permission was not granted."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => body.append(key, value));
    if (media) body.append("media", media);
    try {
      const response = await fetch(`${apiBaseUrl}/api/field-reports`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Report could not be submitted");
      setMessage("Report submitted and added to the GIS map.");
      setForm((current) => ({ ...initialForm, latitude: current.latitude, longitude: current.longitude }));
      setMedia(null);
      await loadReports();
    } catch (error) {
      if (!navigator.onLine || error instanceof TypeError) {
        if (media) {
          setMessage("Offline: report media cannot be queued. Reconnect and submit again.");
        } else {
          const queued = JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
          queued.push(form);
          localStorage.setItem(QUEUE_KEY, JSON.stringify(queued));
          setQueuedCount(queued.length);
          setMessage("Offline report saved on this device and will sync automatically.");
          setForm((current) => ({ ...initialForm, latitude: current.latitude, longitude: current.longitude }));
        }
      } else setMessage(error.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="panel field-report-panel" aria-labelledby="field-report-title">
      <div className="panel-header">
        <div><h2 id="field-report-title">Field Reporting</h2><p>Geo-tag cracks, slope movement, landslides and blocked roads</p></div>
        <span className="field-report-count"><Camera size={14} /> {reports.length} reports{queuedCount ? ` · ${queuedCount} queued` : ""}</span>
      </div>
      <div className="field-report-layout">
        <form className="field-report-form" onSubmit={submit}>
          <select name="report_type" value={form.report_type} onChange={update} aria-label="Report type">
            <option value="crack">Ground crack</option><option value="slope_movement">Slope movement</option>
            <option value="blocked_road">Blocked road</option><option value="landslide">Landslide</option>
            <option value="flooding">Flooding</option><option value="other">Other</option>
          </select>
          <select name="severity" value={form.severity} onChange={update} aria-label="Severity">
            <option value="low">Low</option><option value="moderate">Moderate</option>
            <option value="high">High</option><option value="critical">Critical</option>
          </select>
          <textarea name="description" value={form.description} onChange={update} placeholder="Describe what you observed..." minLength="3" maxLength="1000" required />
          <div className="coordinate-fields">
            <input name="latitude" type="number" step="any" value={form.latitude} onChange={update} aria-label="Latitude" required />
            <input name="longitude" type="number" step="any" value={form.longitude} onChange={update} aria-label="Longitude" required />
            <button type="button" onClick={useLocation}><MapPin size={14} /> Use my location</button>
          </div>
          <div className="report-meta-fields">
            <input name="reporter_name" value={form.reporter_name} onChange={update} placeholder="Reporter name (optional)" />
            <select name="road_status" value={form.road_status} onChange={update} aria-label="Road status">
              <option value="unknown">Road status unknown</option><option value="open">Road open</option>
              <option value="restricted">Road restricted</option><option value="blocked">Road blocked</option>
            </select>
          </div>
          <label className="media-upload"><Upload size={15} /><span>{media?.name ?? "Attach photo/video (max 10 MB)"}</span><input type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" onChange={(event) => setMedia(event.target.files?.[0] ?? null)} /></label>
          <button className="submit-report" type="submit" disabled={submitting}><Send size={14} /> {submitting ? "Submitting..." : "Submit field report"}</button>
          {message && <p className="field-report-message" role="status">{message}</p>}
        </form>
        <div className="recent-field-reports">
          <h3>Recent verified inputs</h3>
          {reports.length === 0 ? <p className="empty-reports">No field reports yet. Submit the first observation.</p> : reports.slice(0, 5).map((report) => (
            <article key={report.id}>
              <span className={`report-severity ${report.severity}`}>{report.severity}</span>
              <div><strong>{report.report_type.replaceAll("_", " ")}</strong><p>{report.description}</p><small>{Number(report.latitude).toFixed(4)}, {Number(report.longitude).toFixed(4)} · {report.road_status}</small></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
