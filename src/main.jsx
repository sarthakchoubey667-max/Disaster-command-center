import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import Portal from "./Portal.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Portal />
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", async () => {
    const registration = await navigator.serviceWorker.register("/sw.js");
    if (registration.waiting) window.dispatchEvent(new Event("disasterai-update-ready"));
    registration.addEventListener("updatefound", () => registration.installing?.addEventListener("statechange", () => {
      if (registration.installing?.state === "installed" && navigator.serviceWorker.controller) window.dispatchEvent(new Event("disasterai-update-ready"));
    }));
    let refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => { if (!refreshing) { refreshing = true; window.location.reload(); } });
  });
}
