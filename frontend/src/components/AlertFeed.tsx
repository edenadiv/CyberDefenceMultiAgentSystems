import { useReplay } from "../lib/replayContext";

export function AlertFeed() {
  const { derived } = useReplay();
  return (
    <div className="panel" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      <div className="panel-title">
        <span className="tick" style={{ background: "var(--red)", boxShadow: "var(--glow-red)" }} />
        <h3>Live Alert &amp; Threat Feed</h3>
      </div>
      <div className="feed">
        {derived.alerts.length === 0 && <div className="empty">awaiting telemetry…</div>}
        {derived.alerts.map((a) => (
          <div key={a.id} className={`alert ${a.level}`}>
            <div className="a-top">
              <span className="a-msg">{a.message}</span>
              <span className={`badge ${a.level}`}>{a.level.toUpperCase()}</span>
            </div>
            <div className="a-meta">
              {(a.ts / 1000).toFixed(2)}s · {a.meta}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
