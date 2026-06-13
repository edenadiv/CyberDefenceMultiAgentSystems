import { describe, expect, it } from "vitest";

import { deriveBeats } from "./director";
import type { CdmasEvent, ReplayData } from "./types";

function ev(p: Partial<CdmasEvent>): CdmasEvent {
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
    ...p,
  };
}

const EVENTS: CdmasEvent[] = [
  ev({
    wall_ms: 50,
    event_type: "ACTION_EXECUTED",
    agent_type: "ATK",
    agent_id: "ATK:ddos",
    payload: { signal: "attack_action", attack_type: "DDOS" },
  }),
  ev({ wall_ms: 120, event_type: "ALERT_PUBLISHED", payload: { deviation_score: 3.1 }, latency_ms: 40 }),
  ev({
    wall_ms: 260,
    event_type: "THREAT_CLASSIFIED",
    agent_type: "ACA",
    payload: { reported: true, classification: "CONFIRMED_THREAT", attack_type: "DDOS", severity: 0.92 },
    latency_ms: 80,
    decision_trace: {
      inputs: {},
      plan_selected: "classify",
      reasoning: "x",
      action: "PUBLISH_THREAT_REPORT",
      confidence: 0.97,
      novelty: 0.02,
    },
  }),
  ev({
    wall_ms: 600,
    event_type: "VOTE_CAST",
    agent_type: "RCA",
    segment: "internal",
    payload: { approved: true, accept_count: 2, member_count: 2 },
    decision_trace: {
      inputs: {},
      plan_selected: "quarantine_vote",
      reasoning: "2/2",
      action: "QUARANTINE",
      votes: { "RCA:internal": "ACCEPT", "RCA:public-facing": "ACCEPT" },
    },
  }),
  ev({
    wall_ms: 700,
    event_type: "ACTION_EXECUTED",
    agent_type: "RCA",
    payload: { signal: "response", action: "THROTTLE", proportionality_score: 0.94 },
    latency_ms: 220,
  }),
  ev({ wall_ms: 900, event_type: "INCIDENT_RESOLVED", agent_type: "RCA", payload: {} }),
];

function replay(events: CdmasEvent[] = EVENTS): ReplayData {
  return {
    scenario: "Scenario 2 - Multi-Segment",
    duration_ms: 2000,
    topology: {
      segments: ["public-facing", "internal"],
      adjacency: { "public-facing": ["internal"], internal: ["public-facing"] },
    },
    events,
    metrics: {
      dr: 1,
      fpr: 0,
      mttr_alert_ms: 50,
      mttr_response_ms: 300,
      availability: 0.999,
      resource_overhead: 0.15,
      social_welfare: 0.95,
      attacker_utility: 0.1,
      coalition_ms: 120,
      evasion_rate: 0,
      concurrent_incidents: 2,
    },
  };
}

describe("deriveBeats", () => {
  it("opens with intro, closes with outro, ordered by time with 1-based index", () => {
    const beats = deriveBeats(replay());
    expect(beats[0].kind).toBe("intro");
    expect(beats[beats.length - 1].kind).toBe("outro");
    beats.forEach((b, i) => {
      expect(b.index).toBe(i + 1);
      if (i > 0) expect(b.atMs).toBeGreaterThanOrEqual(beats[i - 1].atMs);
    });
  });

  it("derives a detect beat citing the deviation and segment", () => {
    const detect = deriveBeats(replay()).find((b) => b.kind === "detect");
    expect(detect).toBeTruthy();
    expect(detect!.caption.toLowerCase()).toContain("public-facing");
    expect(`${detect!.caption} ${detect!.sub}`).toContain("3.1");
  });

  it("surfaces real classifier confidence on the classify beat", () => {
    const c = deriveBeats(replay()).find((b) => b.kind === "classify");
    expect(c).toBeTruthy();
    expect(c!.sub).toContain("0.97");
  });

  it("reflects the vote tally on the vote beat", () => {
    const v = deriveBeats(replay()).find((b) => b.kind === "vote");
    expect(v).toBeTruthy();
    expect(v!.caption).toContain("PASSED");
    expect(v!.sub).toContain("2/2");
  });

  it("includes respond and resolve beats", () => {
    const beats = deriveBeats(replay());
    expect(beats.some((b) => b.kind === "respond")).toBe(true);
    expect(beats.some((b) => b.kind === "resolve")).toBe(true);
  });

  it("gives every beat a non-degenerate camera box and an auto-play window", () => {
    deriveBeats(replay()).forEach((b) => {
      expect(b.camera.w).toBeGreaterThan(0);
      expect(b.camera.h).toBeGreaterThan(0);
      expect(b.windowMs[1]).toBeGreaterThanOrEqual(b.windowMs[0]);
    });
  });

  it("coalesces a flood of same-segment alerts into a single detect beat", () => {
    const flood = [
      ev({ wall_ms: 100, event_type: "ALERT_PUBLISHED", payload: { deviation_score: 3 } }),
      ev({ wall_ms: 150, event_type: "ALERT_PUBLISHED", payload: { deviation_score: 3 } }),
      ev({ wall_ms: 180, event_type: "ALERT_PUBLISHED", payload: { deviation_score: 3 } }),
    ];
    const detects = deriveBeats(replay(flood)).filter((b) => b.kind === "detect");
    expect(detects).toHaveLength(1);
  });

  it("keeps one beat per (kind, segment) across repeated cycles for a walkable narrative", () => {
    const repeated: CdmasEvent[] = [];
    for (const at of [100, 1000, 2000]) {
      repeated.push(
        ev({ wall_ms: at, event_type: "ALERT_PUBLISHED", segment: "internal", payload: { deviation_score: 3 } }),
      );
      repeated.push(
        ev({
          wall_ms: at + 20,
          event_type: "ACTION_EXECUTED",
          agent_type: "RCA",
          segment: "internal",
          payload: { signal: "response", action: "BLOCK" },
        }),
      );
    }
    const beats = deriveBeats(replay(repeated));
    expect(beats.filter((b) => b.kind === "detect")).toHaveLength(1);
    expect(beats.filter((b) => b.kind === "respond")).toHaveLength(1);
    expect(beats).toHaveLength(4); // intro + detect + respond + outro
  });
});
