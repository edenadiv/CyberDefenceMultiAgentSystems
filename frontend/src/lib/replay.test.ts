import { describe, expect, it } from "vitest";

import { deriveState } from "./replay";
import type { CdmasEvent } from "./types";

function ev(partial: Partial<CdmasEvent>): CdmasEvent {
  return {
    event_id: Math.random().toString(36).slice(2),
    lamport_ts: 1,
    wall_ms: 0,
    event_type: "ALERT_PUBLISHED",
    timestamp: "",
    agent_id: "TMA:public-facing",
    agent_type: "TMA",
    segment: "public-facing",
    payload: {},
    latency_ms: 0,
    decision_trace: null,
    ...partial,
  };
}

describe("deriveState", () => {
  const segments = ["public-facing", "internal"];

  it("starts every segment normal", () => {
    const s = deriveState([], 0, segments);
    expect(s.segments["public-facing"].status).toBe("normal");
    expect(s.alerts).toHaveLength(0);
  });

  it("marks a segment under attack on an alert and respects the playhead", () => {
    const events = [
      ev({ wall_ms: 100, event_type: "ALERT_PUBLISHED", payload: { deviation_score: 5 } }),
      ev({ wall_ms: 5000, event_type: "ALERT_PUBLISHED", segment: "internal" }),
    ];
    const s = deriveState(events, 200, segments);
    expect(s.segments["public-facing"].status).toBe("under_attack");
    expect(s.segments["internal"].status).toBe("normal"); // future event not yet reached
    expect(s.counts.alerts).toBe(1);
  });

  it("transitions to mitigating then quarantined as responses arrive", () => {
    const events = [
      ev({ wall_ms: 100, event_type: "ALERT_PUBLISHED", segment: "internal" }),
      ev({
        wall_ms: 150,
        event_type: "ACTION_EXECUTED",
        segment: "internal",
        agent_type: "RCA",
        payload: { signal: "response", action: "QUARANTINE", proportionality_score: 0.73 },
      }),
    ];
    const s = deriveState(events, 200, segments);
    expect(s.segments["internal"].status).toBe("quarantined");
    expect(s.counts.responses).toBe(1);
  });

  it("records coalition formation", () => {
    const events = [
      ev({
        wall_ms: 100,
        event_type: "COALITION_FORMED",
        agent_type: "TIA",
        segment: null,
        payload: { members: ["RCA:a", "RCA:b"], segments: ["public-facing", "internal"], lead_rca: "RCA:a" },
      }),
    ];
    const s = deriveState(events, 200, segments);
    expect(s.coalitions).toHaveLength(1);
    expect(s.coalitions[0].members).toEqual(["RCA:a", "RCA:b"]);
  });
});
