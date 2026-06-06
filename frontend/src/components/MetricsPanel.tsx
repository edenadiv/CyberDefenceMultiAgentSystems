import { Bar, BarChart, Cell, ResponsiveContainer, XAxis } from "recharts";

import { useReplay } from "../lib/replayContext";

interface Tile {
  label: string;
  value: string;
  cls: string;
  target: string;
}

export function MetricsPanel() {
  const { data, derived } = useReplay();
  const m = data.replay.metrics;

  const tiles: Tile[] = [
    {
      label: "Detection Rate",
      value: `${(m.dr * 100).toFixed(1)}%`,
      cls: m.dr > 0.9 ? "ok" : "bad",
      target: "target > 90%",
    },
    {
      label: "False Positive Rate",
      value: `${(m.fpr * 100).toFixed(1)}%`,
      cls: m.fpr < 0.1 ? "ok" : "bad",
      target: "target < 10%",
    },
    {
      label: "MTTR (response)",
      value: `${m.mttr_response_ms.toFixed(0)}ms`,
      cls: m.mttr_response_ms < 1000 ? "ok" : "bad",
      target: "target < 1000ms",
    },
    {
      label: "Availability",
      value: `${(m.availability * 100).toFixed(1)}%`,
      cls: m.availability > 0.99 ? "ok" : "bad",
      target: "target > 99%",
    },
  ];

  const counts = [
    { name: "ALERTS", v: derived.counts.alerts, c: "var(--cyan)" },
    { name: "CLASSIFIED", v: derived.counts.classified, c: "var(--green)" },
    { name: "RESPONSES", v: derived.counts.responses, c: "var(--amber)" },
    { name: "VOTES", v: derived.counts.votes, c: "var(--violet)" },
  ];

  return (
    <div className="panel">
      <div className="panel-title">
        <span className="tick" style={{ background: "var(--green)", boxShadow: "var(--glow-green)" }} />
        <h3>Live Performance Metrics vs SRS Targets</h3>
      </div>
      <div className="metric-grid">
        {tiles.map((t) => (
          <div className="metric" key={t.label}>
            <div className="label">{t.label}</div>
            <div className={`value ${t.cls}`}>{t.value}</div>
            <div className="target">{t.target}</div>
          </div>
        ))}
      </div>
      <div style={{ height: 92, marginTop: 12 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={counts} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <XAxis
              dataKey="name"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 9, fill: "#6c7f97" }}
              axisLine={false}
              tickLine={false}
            />
            <Bar dataKey="v" radius={[3, 3, 0, 0]} label={{ position: "top", fill: "#cddcee", fontSize: 11 }}>
              {counts.map((c) => (
                <Cell key={c.name} fill={c.c} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
