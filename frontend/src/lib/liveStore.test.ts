import { describe, expect, it } from "vitest";

import {
  type StreamFrame,
  initialLiveState,
  liveDerived,
  liveMetrics,
  liveReduce,
} from "./liveStore";

const frame = (
  kind: string,
  payload: Record<string, unknown>,
  ts_ms = 0,
  seq = 1,
): StreamFrame => ({ kind, server_seq: seq, ts_ms, payload });

const alertEvent = (wall_ms: number) => ({
  event_id: `a${wall_ms}`,
  lamport_ts: 1,
  wall_ms,
  event_type: "ALERT_PUBLISHED",
  timestamp: "",
  agent_id: "TMA:public-facing",
  agent_type: "TMA",
  segment: "public-facing",
  payload: { deviation_score: 3 },
  latency_ms: 0,
  decision_trace: null,
});

describe("liveReduce", () => {
  it("sets topology from a topology frame", () => {
    const s = liveReduce(
      initialLiveState,
      frame("topology", {
        segments: ["public-facing", "internal"],
        adjacency: { "public-facing": ["internal"], internal: ["public-facing"] },
      }),
    );
    expect(s.topology.segments).toEqual(["public-facing", "internal"]);
  });

  it("accumulates agent events and tracks the latest timestamp", () => {
    const s = liveReduce(initialLiveState, frame("agent_event", alertEvent(120), 120));
    expect(s.events).toHaveLength(1);
    expect(s.lastTs).toBe(120);
  });

  it("synthesizes an attacker flow from a manual DoS sim_event", () => {
    const s = liveReduce(
      initialLiveState,
      frame("sim_event", { signal: "manual_dos", segment: "public-facing", attack_type: "DDOS" }, 50),
    );
    const atk = s.events.find((e) => e.payload?.signal === "attack_action");
    expect(atk).toBeTruthy();
    expect(atk!.agent_type).toBe("ATK");
    expect(atk!.segment).toBe("public-facing");
  });

  it("updates connection and simulation state", () => {
    let s = liveReduce(
      initialLiveState,
      frame("connection_status", {
        agents_connected: 5,
        agents_total: 5,
        bus_connected: true,
        stream_connected: true,
      }),
    );
    s = liveReduce(
      s,
      frame("simulation_state", { mode: "step", paused: false, awaiting_next: true, round: 3 }),
    );
    expect(s.conn.agents_connected).toBe(5);
    expect(s.conn.stream_connected).toBe(true);
    expect(s.sim.mode).toBe("step");
    expect(s.sim.awaiting_next).toBe(true);
  });
});

describe("liveDerived", () => {
  it("derives the same DerivedState shape from accumulated live events", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing"], adjacency: { "public-facing": [] } }),
    );
    s = liveReduce(s, frame("agent_event", alertEvent(120), 120));
    const d = liveDerived(s);
    expect(d.segments["public-facing"].status).toBe("under_attack");
    expect(d.counts.alerts).toBe(1);
  });
});

const responseEvent = (wall_ms: number, latency_ms: number) => ({
  event_id: `r${wall_ms}`,
  lamport_ts: 1,
  wall_ms,
  event_type: "ACTION_EXECUTED",
  timestamp: "",
  agent_id: "RCA:public-facing",
  agent_type: "RCA",
  segment: "public-facing",
  payload: { signal: "response", action: "BLOCK" },
  latency_ms,
  decision_trace: null,
});

describe("liveMetrics", () => {
  it("availability drops and incidents rise while a segment is under attack", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing", "internal"], adjacency: {} }),
    );
    s = liveReduce(s, frame("agent_event", alertEvent(100), 100));
    const m = liveMetrics(s);
    expect(m.availability).toBeCloseTo(0.5); // 1 of 2 segments compromised
    expect(m.concurrent_incidents).toBe(1);
  });

  it("computes mean response latency from real events", () => {
    let s = liveReduce(
      initialLiveState,
      frame("topology", { segments: ["public-facing"], adjacency: {} }),
    );
    s = liveReduce(s, frame("agent_event", responseEvent(200, 120), 200));
    s = liveReduce(s, frame("agent_event", responseEvent(260, 80), 260));
    expect(liveMetrics(s).mttr_response_ms).toBeCloseTo(100); // (120 + 80) / 2
  });

  it("returns safe zeros (no NaN) for an empty stream", () => {
    const m = liveMetrics(initialLiveState);
    expect(m.mttr_response_ms).toBe(0);
    expect(m.availability).toBe(1);
    expect(Number.isNaN(m.availability)).toBe(false);
  });
});
