import { useEffect, useState } from "react";
import App from "./App";
import AuthScreen from "./AuthScreen";
import RoleDashboard from "./RoleDashboard";
import HospitalDashboard from "./HospitalDashboard";
import InstallApp from "./InstallApp";
import WelcomeScreen from "./WelcomeScreen";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "disasterai_session";

export default function Portal() {
  const [session, setSession] = useState(null);
  const [checking, setChecking] = useState(true);
  const [showWelcome, setShowWelcome] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return setChecking(false);
    fetch(`${API_BASE_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data) => setSession({ token, user: data.user }))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setChecking(false));
  }, []);

  const onLogin = (data) => {
    localStorage.setItem(TOKEN_KEY, data.token);
    setSession({ token: data.token, user: data.user });
  };
  const logout = () => {
    if (session?.token) fetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${session.token}` } }).catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    setSession(null);
  };

  let screen;
  if (checking) screen = <div className="portal-loading"><span />Checking secure access…</div>;
  else if (!session && showWelcome) screen = <WelcomeScreen onContinue={() => setShowWelcome(false)} />;
  else if (!session) screen = <AuthScreen apiBaseUrl={API_BASE_URL} onLogin={onLogin} />;
  else if (session.user.role === "operator") screen = <App session={session} onLogout={logout} />;
  else if (session.user.role === "hospital") screen = <HospitalDashboard apiBaseUrl={API_BASE_URL} session={session} onLogout={logout} />;
  else screen = <RoleDashboard apiBaseUrl={API_BASE_URL} session={session} onLogout={logout} />;
  return <>{screen}<InstallApp /></>;
}
