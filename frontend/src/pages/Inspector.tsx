import { useMemo, useState } from "react";

import { useReplay } from "../lib/replayContext";

const DESIRES: Record<string, string[]> = {
  TMA: ["maximize detection rate", "minimize false positives", "alert < 100ms"],
  ACA: ["classify < 200ms", "accuracy > 90% / FPR < 8%", "improve model online"],
  RCA: ["respond < 500ms", "maximize availability", "least-disruptive action"],
  TIA: ["global threat model", "correlate multi-segment", "trigger coalitions"],
  RAA: ["allocate to highest severity", "auction < 300ms", "overhead < 40%"],
};

export function Inspector() {
  const { data, t } = useReplay();

  const events = useMemo(
    () => data.replay.events.filter((e) => e.wall_ms <= t),
    [data, t],
  );
  const agentIds = useMemo(() => {
    const ids = new Set(events.map((e) => e.agent_id));
    return Array.from(ids).sort();
  }, [events]);

  const [selected, setSelected] = useState<string | null>(null);
  const agent = selected && agentIds.includes(selected) ? selected : (agentIds[0] ?? null);

  const agentEvents = agent ? events.filter((e) => e.agent_id === agent) : [];
  const latest = [...agentEvents].reverse().find((e) => e.decision_trace);
  const agentType = agent?.split(":")[0] ?? "";

  return (
    <div className="inspector-grid">
      <div className="panel">
        <div className="panel-title">
          <span className="tick" />
          <h3>Agents ({agentIds.length})</h3>
        </div>
        <div className="agent-list">
          {agentIds.map((id) => (
            <div
              key={id}
              className={`agent-item ${id === agent ? "sel" : ""}`}
              onClick={() => setSelected(id)}
            >
              <span>{id}</span>
              <span style={{ color: "var(--faint)" }}>
                {events.filter((e) => e.agent_id === id).length}
              </span>
            </div>
          ))}
          {agentIds.length === 0 && <div className="empty">scrub the replay to populate agents</div>}
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">
          <span className="tick" style={{ background: "var(--green)" }} />
          <h3>{agent ?? "—"} · BDI State</h3>
        </div>
        {agent ? (
          <>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Current Intention</div>
            <div className="kv">
              <span className="k">plan</span>
              <span>{latest?.decision_trace?.plan_selected ?? "idle"}</span>
            </div>
            <div className="kv">
              <span className="k">action</span>
              <span style={{ color: "var(--amber)" }}>{latest?.decision_trace?.action ?? "—"}</span>
            </div>
            <div className="kv">
              <span className="k">last reasoning</span>
            </div>
            <div className="mono" style={{ fontSize: 11, color: "var(--cyan)", marginBottom: 16 }}>
              {latest?.decision_trace?.reasoning ?? "—"}
            </div>

            <div className="eyebrow" style={{ marginBottom: 8 }}>Desires (ranked)</div>
            {(DESIRES[agentType] ?? []).map((d, i) => (
              <div className="kv" key={d}>
                <span className="k">{i + 1}.</span>
                <span style={{ color: i === 0 ? "var(--green)" : "var(--dim)" }}>{d}</span>
              </div>
            ))}
          </>
        ) : (
          <div className="empty">no agent selected</div>
        )}
      </div>

      <div className="panel">
        <div className="panel-title">
          <span className="tick" style={{ background: "var(--cyan)" }} />
          <h3>Strategy Trace (live)</h3>
        </div>
        <div className="trace">
          {agentEvents.length === 0 && <div className="empty">no activity yet</div>}
          {[...agentEvents].reverse().slice(0, 60).map((e) => (
            <div className="row" key={e.event_id}>
              <span className="ts">{(e.wall_ms / 1000).toFixed(2)}s</span>
              <span className="kw">{e.event_type.replace(/_/g, " ").toLowerCase()}</span>
              <span style={{ color: "var(--dim)" }}>
                {e.decision_trace?.action ?? e.payload?.signal ?? ""}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
