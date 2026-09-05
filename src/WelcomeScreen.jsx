import { Activity, ArrowRight, CloudRain, MapPinned, ShieldAlert, Siren, Wifi } from "lucide-react";

export default function WelcomeScreen({ onContinue }) {
  return <main className="welcome-screen">
    <div className="welcome-orb welcome-orb-one"/><div className="welcome-orb welcome-orb-two"/>
    <header className="welcome-top"><div className="welcome-logo"><span><ShieldAlert size={25}/></span><div><strong>DisasterAI</strong><small>EARLY WARNING NETWORK</small></div></div><div className="welcome-online"><i/> Network live</div></header>
    <section className="welcome-hero">
      <div className="welcome-copy"><span className="welcome-kicker"><Activity size={14}/> NORTH EASTERN INDIA RESPONSE SYSTEM</span><h1>Predict danger.<br/>Connect responders.<br/><em>Protect lives.</em></h1><p>AI-powered landslide warnings, live disaster intelligence and verified emergency response—all in one connected app.</p><p className="welcome-hindi">खतरे की समय पर चेतावनी। तेज़ सहायता। सुरक्षित समुदाय।</p><div className="welcome-actions"><button onClick={onContinue}>Open DisasterAI <ArrowRight size={18}/></button><span><Wifi size={14}/> Low-network &amp; offline ready</span></div></div>
      <div className="welcome-visual" aria-hidden="true"><div className="radar-ring ring-one"/><div className="radar-ring ring-two"/><div className="radar-ring ring-three"/><div className="radar-sweep"/><div className="radar-center"><ShieldAlert size={34}/></div><div className="signal-card signal-weather"><CloudRain size={17}/><span>Weather</span><b>LIVE</b></div><div className="signal-card signal-map"><MapPinned size={17}/><span>Risk Map</span><b>ACTIVE</b></div><div className="signal-card signal-response"><Siren size={17}/><span>Response</span><b>READY</b></div></div>
    </section>
    <footer className="welcome-features"><article><CloudRain size={18}/><div><strong>Early Warning</strong><span>Weather and terrain intelligence</span></div></article><article><MapPinned size={18}/><div><strong>Live Risk Map</strong><span>Zones, routes and shelters</span></div></article><article><Siren size={18}/><div><strong>Connected Response</strong><span>Police, fire, rescue and hospitals</span></div></article></footer>
  </main>;
}
