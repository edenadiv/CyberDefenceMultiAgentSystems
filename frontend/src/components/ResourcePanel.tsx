import { useReplay } from "../lib/replayContext";

export function ResourcePanel() {
  const { data, derived } = useReplay();
  const overhead = derived.overhead || data.replay.metrics.resource_overhead;
  const pct = Math.min(100, overhead * 100);
  const cap = 40;
  const over = pct > cap;

  return (
    <div className="panel">
      <div className="panel-title">
        <span className="tick" style={{ background: "var(--amber)", boxShadow: "var(--glow-amber)" }} />
        <h3>Resource Allocation (RAA)</h3>
      </div>
      <div className="mono" style={{ fontSize: 12, color: "var(--dim)", marginBottom: 6 }}>
        MAS Host Overhead{" "}
        <span className={over ? "bad" : "ok"} style={{ fontWeight: 700 }}>
          {pct.toFixed(1)}%
        </span>{" "}
        / {cap}% cap
      </div>
      <div
        style={{
          height: 14,
          borderRadius: 7,
          background: "rgba(86,122,160,0.15)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: over ? "var(--red)" : "linear-gradient(90deg, var(--green), var(--cyan))",
            transition: "width .4s ease",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `${cap}%`,
            top: 0,
            bottom: 0,
            width: 2,
            background: "var(--amber)",
          }}
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 14 }}>
        <Stat k="Concurrent Incidents" v={String(data.replay.metrics.concurrent_incidents)} />
        <Stat k="Social Welfare" v={data.replay.metrics.social_welfare.toFixed(3)} ok />
        <Stat k="Attacker Utility" v={data.replay.metrics.attacker_utility.toFixed(3)} />
        <Stat
          k="Evasion Rate"
          v={(data.replay.metrics.evasion_rate ?? 0).toFixed(3)}
        />
      </div>
    </div>
  );
}

function Stat({ k, v, ok }: { k: string; v: string; ok?: boolean }) {
  return (
    <div className="kv" style={{ borderBottom: "none" }}>
      <span className="k">{k}</span>
      <span className={ok ? "ok" : ""} style={{ fontWeight: 700 }}>
        {v}
      </span>
    </div>
  );
}
