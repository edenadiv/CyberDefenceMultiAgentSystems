import { useState } from "react";

import { useReplay } from "../lib/replayContext";

export function Validator() {
  const { data } = useReplay();
  const scenarios = data.validation;
  const [open, setOpen] = useState(0);

  const passCount = scenarios.filter((s) => s.passed).length;
  const allFr = new Set<string>();
  const passFr = new Set<string>();
  for (const s of scenarios)
    for (const c of s.constraints) {
      allFr.add(c.fr_id);
      if (c.status === "PASS") passFr.add(c.fr_id);
    }
  const sel = scenarios[open];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: 16 }}>
      <div className="panel">
        <div className="panel-title">
          <span className="tick" style={{ background: "var(--green)" }} />
          <h3>Replay &amp; Constraint Validation</h3>
        </div>
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 40,
            fontWeight: 700,
            color: passCount === scenarios.length ? "var(--green)" : "var(--amber)",
            textShadow: passCount === scenarios.length ? "var(--glow-green)" : "none",
          }}
        >
          {passCount} / {scenarios.length}
        </div>
        <div className="eyebrow" style={{ marginBottom: 18 }}>
          scenarios passed · {passFr.size} FRs verified
        </div>

        {scenarios.map((s, i) => (
          <div
            key={s.name}
            className="scenario-row"
            style={{ cursor: "pointer", borderColor: i === open ? "var(--line-bright)" : undefined }}
            onClick={() => setOpen(i)}
          >
            <span className={`verdict ${s.passed ? "pass" : "fail"}`}>
              {s.passed ? "PASS" : "FAIL"}
            </span>
            <span style={{ flex: 1 }}>{s.name}</span>
            <span className="mono" style={{ color: "var(--dim)", fontSize: 12 }}>
              SW {s.social_welfare.toFixed(3)}
            </span>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-title">
          <span className="tick" style={{ background: "var(--cyan)" }} />
          <h3>{sel.name} · Functional Requirements</h3>
        </div>
        <div style={{ marginBottom: 14 }}>
          {Object.entries(sel.criteria).map(([k, v]) => (
            <div className="kv" key={k}>
              <span className="k">{k}</span>
              <span className={v ? "ok" : "bad"} style={{ fontWeight: 700 }}>
                {v ? "PASS" : "FAIL"}
              </span>
            </div>
          ))}
        </div>
        <div className="fr-grid">
          {sel.constraints.map((c) => (
            <div className="fr" key={c.fr_id}>
              <div className="fr-id">{c.fr_id}</div>
              <div className="fr-desc">{c.description}</div>
              <div className={`fr-st st-${c.status}`}>
                {c.status} · {c.observed}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
