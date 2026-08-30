import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const waterData = [
  { time: "8 AM", level: 1.2 }, { time: "9 AM", level: 1.4 },
  { time: "10 AM", level: 1.7 }, { time: "11 AM", level: 2.0 },
  { time: "12 PM", level: 2.4 },
];

function SensorChart() {
  return (
    <div className="sensor-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={waterData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="time" /><YAxis /><Tooltip /><Line type="monotone" dataKey="level" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} /></LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default SensorChart;