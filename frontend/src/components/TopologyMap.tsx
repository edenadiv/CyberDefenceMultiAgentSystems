import { SLOT_ORDER, SLOTS } from "../lib/graph";
import type { SegStatus } from "../lib/replay";
import { useReplay } from "../lib/replayContext";

const LABELS: Record<string, string> = {
  internal: "Internal User Subnet",
  server: "Server Zone",
  "public-facing": "Public-Facing Services",
  "sec-mon": "Security Monitoring",
};

const SHORT_LABELS: Record<string, string> = {
  internal: "Internal",
  server: "Server Zone",
  "public-facing": "Public-Facing",
  "sec-mon": "Sec-Mon",
};

const STATUS_TEXT: Record<SegStatus, string> = {
  normal: "Nominal",
  under_attack: "Under Attack",
  mitigating: "Mitigating",
  quarantined: "Quarantined",
};

const STATUS_COLOR: Record<SegStatus, string> = {
  normal: "var(--green)",
  under_attack: "var(--red)",
  mitigating: "var(--cyan)",
  quarantined: "var(--violet)",
};

const AGENT_CHIPS = [
  { letter: "T", name: "Traffic Monitor" },
  { letter: "A", name: "Anomaly Classifier" },
  { letter: "R", name: "Response Coordinator" },
];

const NODE_W = 100;
const NODE_H = 66;

function slotRank(seg: string): number {
  const i = SLOT_ORDER.indexOf(seg);
  return i === -1 ? SLOT_ORDER.length : i;
}

export function TopologyMap() {
  const { data, derived } = useReplay();

  const segs = [...data.topology.segments].sort((a, b) => slotRank(a) - slotRank(b));
  const slots = SLOTS[segs.length] ?? SLOTS[4];
  const pos = new Map(segs.map((s, i) => [s, slots[Math.min(i, slots.length - 1)]]));

  const seen = new Set<string>();
  const edges: Array<[string, string]> = [];
  for (const [seg, neighbors] of Object.entries(data.topology.adjacency)) {
    for (const n of neighbors) {
      if (!pos.has(seg) || !pos.has(n)) continue;
      const key = [seg, n].sort().join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push([seg, n]);
    }
  }

  return (
    <div className="panel col-topology">
      <div className="panel-title">
        <span className="tick" />
        <h3>Network Topology</h3>
      </div>
      <div className="topo-body">
        <svg viewBox="0 0 240 280" preserveAspectRatio="xMidYMin meet" style={{ width: "100%" }}>
          {edges.map(([a, b]) => {
            const pa = pos.get(a)!;
            const pb = pos.get(b)!;
            return (
              <line
                key={`${a}|${b}`}
                x1={pa.x}
                y1={pa.y}
                x2={pb.x}
                y2={pb.y}
                stroke="var(--line-bright)"
                strokeWidth={1.5}
                strokeDasharray="4 6"
                opacity={0.9}
              />
            );
          })}
          {segs.map((seg) => {
            const { x, y } = pos.get(seg)!;
            const st = derived.segments[seg]?.status ?? "normal";
            const color = STATUS_COLOR[st];
            const alarmed = st !== "normal";
            return (
              <g key={seg}>
                <title>{`${LABELS[seg] ?? seg} — ${STATUS_TEXT[st]}`}</title>
                <rect
                  x={x - NODE_W / 2}
                  y={y - NODE_H / 2}
                  width={NODE_W}
                  height={NODE_H}
                  rx={10}
                  fill="var(--panel-solid)"
                  stroke={color}
                  strokeWidth={alarmed ? 2.4 : 1.4}
                  style={{ filter: alarmed ? `drop-shadow(0 0 8px ${color})` : "none" }}
                />
                <text
                  x={x}
                  y={y - 12}
                  textAnchor="middle"
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 11,
                    fontWeight: 700,
                    fill: "var(--text)",
                  }}
                >
                  {SHORT_LABELS[seg] ?? seg}
                </text>
                <text
                  x={x}
                  y={y + 2}
                  textAnchor="middle"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 8,
                    letterSpacing: 0.8,
                    fill: color,
                  }}
                >
                  {STATUS_TEXT[st].toUpperCase()}
                </text>
                {AGENT_CHIPS.map(({ letter, name }, i) => {
                  const cx = x - 27 + i * 20;
                  return (
                    <g key={letter}>
                      <title>{name}</title>
                      <rect
                        x={cx}
                        y={y + 9}
                        width={14}
                        height={14}
                        rx={4}
                        fill={alarmed ? "var(--green)" : "transparent"}
                        stroke={alarmed ? "var(--green)" : "var(--line)"}
                        strokeWidth={1}
                      />
                      <text
                        x={cx + 7}
                        y={y + 19}
                        textAnchor="middle"
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 8,
                          fontWeight: 700,
                          fill: alarmed ? "var(--bg)" : "var(--dim)",
                        }}
                      >
                        {letter}
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
        <div className="flow-legend">
          {(Object.keys(STATUS_TEXT) as SegStatus[]).map((s) => (
            <span key={s} className="flow-legend-item">
              <span className="flow-legend-dot" style={{ background: STATUS_COLOR[s] }} />
              {STATUS_TEXT[s]}
            </span>
          ))}
          <span className="flow-legend-item">
            <svg width="18" height="6" aria-hidden="true">
              <line
                x1={0}
                y1={3}
                x2={18}
                y2={3}
                stroke="var(--line-bright)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
            </svg>
            Link = lateral-movement route
          </span>
        </div>
        <div className="topo-foot">
          <span className="topo-foot-label">Global Agents</span>
          <div className="agent-chips">
            <span
              className="chip on"
              style={{ background: "var(--cyan)", borderColor: "var(--cyan)" }}
              title="Threat Intelligence Agent"
            >
              TIA
            </span>
            <span
              className="chip on"
              style={{ background: "var(--cyan)", borderColor: "var(--cyan)" }}
              title="Resource Allocator Agent"
            >
              RAA
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
