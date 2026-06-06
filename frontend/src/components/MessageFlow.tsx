import { useReplay } from "../lib/replayContext";

const NODES: Record<string, { x: number; y: number; color: string }> = {
  TMA: { x: 90, y: 185, color: "var(--cyan)" },
  ACA: { x: 250, y: 70, color: "var(--green)" },
  RCA: { x: 440, y: 175, color: "var(--amber)" },
  TIA: { x: 180, y: 305, color: "var(--violet)" },
  RAA: { x: 410, y: 320, color: "var(--cyan)" },
};

const KIND_COLOR: Record<string, string> = {
  alert: "var(--cyan)",
  report: "var(--green)",
  coalition: "var(--violet)",
  correlate: "var(--violet)",
  vote: "var(--amber)",
  grant: "var(--cyan)",
  mitigate: "var(--green)",
};

export function MessageFlow() {
  const { derived } = useReplay();
  const coalition = derived.coalitions[0];

  return (
    <div className="panel" style={{ flex: 1, minHeight: 360 }}>
      <div className="panel-title">
        <span className="tick" />
        <h3>Agent Message Flow &amp; Coalition Overlay</h3>
      </div>
      <svg viewBox="0 0 560 380" style={{ width: "100%", height: "100%" }}>
        <style>{`
          .edge { stroke-dasharray: 6 8; animation: dash 0.7s linear infinite; }
          @keyframes dash { to { stroke-dashoffset: -28; } }
          .node-c { transition: all .3s ease; }
        `}</style>

        {coalition && (
          <g>
            <ellipse
              cx={290}
              cy={195}
              rx={235}
              ry={165}
              fill="rgba(176,139,255,0.05)"
              stroke="var(--violet)"
              strokeDasharray="4 6"
              strokeWidth={1.2}
            />
            <text x={70} y={32} className="flow-label" fill="var(--violet)">
              COALITION · {coalition.members.length} members
            </text>
          </g>
        )}

        {derived.flows.map((f, i) => {
          const a = NODES[f.from];
          const b = NODES[f.to];
          if (!a || !b) return null;
          return (
            <line
              key={`${f.from}-${f.to}-${i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={KIND_COLOR[f.kind] ?? "var(--cyan)"}
              strokeWidth={1.6}
              className="edge"
              opacity={0.9}
            />
          );
        })}

        {Object.entries(NODES).map(([name, n]) => {
          const active = derived.flows.some((f) => f.from === name || f.to === name);
          return (
            <g key={name}>
              <circle
                className="node-c"
                cx={n.x}
                cy={n.y}
                r={active ? 30 : 26}
                fill="rgba(7,12,20,0.9)"
                stroke={n.color}
                strokeWidth={active ? 2.4 : 1.4}
                style={{ filter: active ? `drop-shadow(0 0 10px ${n.color})` : "none" }}
              />
              <text
                x={n.x}
                y={n.y + 5}
                textAnchor="middle"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: 15,
                  fontWeight: 700,
                  fill: n.color,
                }}
              >
                {name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
