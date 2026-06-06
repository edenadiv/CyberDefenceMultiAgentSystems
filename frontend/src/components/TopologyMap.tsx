import { useReplay } from "../lib/replayContext";
import type { SegStatus } from "../lib/replay";

const LABELS: Record<string, string> = {
  internal: "Internal User Subnet",
  server: "Server Zone",
  "public-facing": "Public-Facing Services",
  "sec-mon": "Security Monitoring",
};

const STATUS_TEXT: Record<SegStatus, string> = {
  normal: "Nominal",
  under_attack: "Under Attack",
  mitigating: "Mitigating",
  quarantined: "Quarantined",
};

export function TopologyMap() {
  const { data, derived } = useReplay();
  return (
    <div className="panel col-topology">
      <div className="panel-title">
        <span className="tick" />
        <h3>Network Topology</h3>
      </div>
      <div className="seg-list">
        {data.topology.segments.map((seg) => {
          const st = derived.segments[seg]?.status ?? "normal";
          return (
            <div key={seg} className={`seg-card ${st}`}>
              <div className="seg-head">
                <span className="seg-name">{LABELS[seg] ?? seg}</span>
                <span className={`seg-status s-${st}`}>{STATUS_TEXT[st]}</span>
              </div>
              <div className="seg-flows mono">zone · {seg}</div>
              <div className="agent-chips">
                {["T", "A", "R"].map((c) => (
                  <span key={c} className={`chip ${st !== "normal" ? "on" : ""}`}>
                    {c}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
        <div className="seg-card normal" style={{ borderLeftColor: "var(--cyan)" }}>
          <div className="seg-head">
            <span className="seg-name">Global Agents</span>
          </div>
          <div className="agent-chips">
            <span className="chip on" style={{ background: "var(--cyan)", borderColor: "var(--cyan)" }}>
              TIA
            </span>
            <span className="chip on" style={{ background: "var(--cyan)", borderColor: "var(--cyan)" }}>
              RAA
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
