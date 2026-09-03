import { Bell, Languages, Radio } from "lucide-react";
import { useMemo, useState } from "react";

const copy = {
  en: { title: "Multilingual Early Warning", subtitle: "Current risk converted into a community-ready message", risk: "risk", rain: "rainfall", river: "river level", action: "Avoid unstable slopes and follow official evacuation instructions.", enable: "Enable device alerts", ready: "Device alerts enabled" },
  hi: { title: "बहुभाषी पूर्व चेतावनी", subtitle: "वर्तमान जोखिम को समुदाय के लिए तैयार संदेश में बदला गया", risk: "जोखिम", rain: "वर्षा", river: "नदी स्तर", action: "अस्थिर ढलानों से दूर रहें और आधिकारिक निकासी निर्देशों का पालन करें।", enable: "डिवाइस अलर्ट चालू करें", ready: "डिवाइस अलर्ट चालू हैं" },
  as: { title: "বহুভাষিক আগতীয়া সতৰ্কবাণী", subtitle: "বৰ্তমান বিপদক সমাজৰ বাবে উপযোগী বাৰ্তালৈ ৰূপান্তৰ কৰা হৈছে", risk: "বিপদ", rain: "বৰষুণ", river: "নদীৰ স্তৰ", action: "অস্থিৰ ঢালৰ পৰা আঁতৰি থাকক আৰু চৰকাৰী স্থানান্তৰৰ নিৰ্দেশ মানক।", enable: "ডিভাইচ সতৰ্কতা চালু কৰক", ready: "ডিভাইচ সতৰ্কতা চালু আছে" },
};

export default function WarningCenter({ externalData, riskScore }) {
  const [language, setLanguage] = useState("en");
  const [notificationState, setNotificationState] = useState(typeof Notification !== "undefined" ? Notification.permission : "unsupported");
  const text = copy[language];
  const risk = Number(riskScore ?? 0);
  const level = risk >= 80 ? "CRITICAL" : risk >= 60 ? "HIGH" : risk >= 35 ? "MODERATE" : "LOW";
  const features = externalData?.landslide_features ?? {};
  const place = externalData?.sources?.geocoding?.data?.results?.[0]?.formatted_address?.split(",").slice(0, 3).join(", ") || "Monitored zone";
  const message = useMemo(() => `${place}: ${text.risk} ${level} (${risk.toFixed(1)}/100), ${text.rain} ${Number(features.rainfall_mm ?? 0).toFixed(1)} mm, ${text.river} ${features.water_level != null ? `${Number(features.water_level).toFixed(2)} m` : "--"}. ${text.action}`, [features.rainfall_mm, features.water_level, level, place, risk, text]);

  const enableNotifications = async () => {
    if (!("Notification" in window)) return setNotificationState("unsupported");
    const permission = await Notification.requestPermission();
    setNotificationState(permission);
    if (permission === "granted") new Notification("DisasterAI", { body: message, icon: "/favicon.svg" });
  };

  return (
    <section className="panel warning-center" aria-labelledby="warning-center-title">
      <div className="panel-header">
        <div><h2 id="warning-center-title">{text.title}</h2><p>{text.subtitle}</p></div>
        <div className="language-picker"><Languages size={14} /><select value={language} onChange={(event) => setLanguage(event.target.value)} aria-label="Warning language"><option value="en">English</option><option value="hi">हिन्दी</option><option value="as">অসমীয়া</option></select></div>
      </div>
      <div className="warning-message">
        <div className={`warning-level ${level.toLowerCase()}`}><Radio size={17} /><span>{level}</span></div>
        <p>{message}</p>
        <button type="button" onClick={enableNotifications} disabled={notificationState === "granted"}><Bell size={14} />{notificationState === "granted" ? text.ready : text.enable}</button>
      </div>
      <div className="warning-channels"><span><i className="online" /> In-app live</span><span><i className={notificationState === "granted" ? "online" : ""} /> Device notification</span><span><i /> SMS requires provider credentials</span></div>
    </section>
  );
}
