import { Ambulance, MapPin, Radio, Users } from "lucide-react";
import { useState } from "react";

const initialTeams = [
  { id: 1, name: "Rescue Team Alpha", location: "Guwahati Central", members: 8, status: "available" },
  { id: 2, name: "Medical Response 02", location: "Dispur Sector", members: 5, status: "available" },
  { id: 3, name: "Road Clearance Unit", location: "NH15 Corridor", members: 6, status: "deployed" },
];

export default function RescueTeams() {
  const [teams, setTeams] = useState(initialTeams);
  const toggle = (id) => setTeams((current) => current.map((team) => team.id === id ? { ...team, status: team.status === "deployed" ? "available" : "deployed" } : team));
  return (
    <section className="panel rescue-panel" id="rescue-teams" aria-labelledby="rescue-teams-title">
      <div className="panel-header"><div><h2 id="rescue-teams-title">Rescue Teams</h2><p>Operational response assignment board</p></div><span className="rescue-count"><Users size={14} /> {teams.filter((team) => team.status === "available").length} available</span></div>
      <div className="rescue-grid">{teams.map((team) => <article key={team.id}>
        <div className="rescue-icon">{team.id === 2 ? <Ambulance size={19} /> : <Radio size={19} />}</div>
        <div className="rescue-copy"><strong>{team.name}</strong><span><MapPin size={11} /> {team.location}</span><small>{team.members} responders · {team.status}</small></div>
        <button type="button" className={team.status} onClick={() => toggle(team.id)}>{team.status === "deployed" ? "Mark available" : "Deploy team"}</button>
      </article>)}</div>
    </section>
  );
}
