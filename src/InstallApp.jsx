import { Download, RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";

export default function InstallApp() {
  const [installEvent, setInstallEvent] = useState(null);
  const [updateReady, setUpdateReady] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => {
    const onInstall = (event) => { event.preventDefault(); setInstallEvent(event); };
    const onInstalled = () => setInstallEvent(null);
    const onUpdate = () => setUpdateReady(true);
    window.addEventListener("beforeinstallprompt", onInstall);
    window.addEventListener("appinstalled", onInstalled);
    window.addEventListener("disasterai-update-ready", onUpdate);
    return () => { window.removeEventListener("beforeinstallprompt", onInstall); window.removeEventListener("appinstalled", onInstalled); window.removeEventListener("disasterai-update-ready", onUpdate); };
  }, []);
  const install = async () => { if (!installEvent) return; await installEvent.prompt(); const choice = await installEvent.userChoice; if (choice.outcome === "accepted") setInstallEvent(null); };
  const update = () => navigator.serviceWorker?.getRegistration().then((registration) => registration?.waiting?.postMessage({ type: "SKIP_WAITING" }));
  if ((!installEvent && !updateReady) || dismissed) return null;
  return <aside className="app-action" role="status"><div className="app-action-icon">{updateReady ? <RefreshCw size={19}/> : <Download size={19}/>}</div><div><strong>{updateReady ? "DisasterAI update ready" : "Install DisasterAI App"}</strong><span>{updateReady ? "Reload to use the latest secure version." : "Add it to your phone home screen for faster access."}</span></div><button className="app-action-primary" onClick={updateReady ? update : install}>{updateReady ? "Update" : "Install"}</button><button className="app-action-close" aria-label="Dismiss" onClick={() => setDismissed(true)}><X size={15}/></button></aside>;
}
