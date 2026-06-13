/* Director mode: turn a recorded scenario into an ordered list of cinematic "beats".

   A beat is one narrated step — where the playback clock should land, which agents to
   focus, and a caption written from the REAL event data (deviation σ, classifier
   confidence/novelty, vote tally, response latency). The Director component walks these
   beats; nothing here touches React, so it is unit-tested in isolation. */
import { boundingBox, type ViewBox } from "./graph";
import { attackerNodeFor, shortScenarioName } from "./replay";
import type { CdmasEvent, ReplayData } from "./types";

export type BeatKind =
  | "intro"
  | "attack"
  | "detect"
  | "classify"
  | "correlate"
  | "coalition"
  | "vote"
  | "auction"
  | "respond"
  | "resolve"
  | "outro";

export interface Beat {
  id: string;
  index: number; // 1-based, for the ribbon "step 2/9"
  kind: BeatKind;
  atMs: number; // where the clock lands (and holds, in manual mode)
  windowMs: [number, number]; // [seek-from, hold-at] play window for auto mode
  camera: ViewBox; // message-canvas box to frame this beat
  highlight: { nodes: string[]; segments: string[] };
  caption: string; // narration headline
  sub?: string; // secondary line — the real numbers behind the decision
  event?: CdmasEvent; // source event (drives the decision pop-over in Phase 4)
}

function num(v: unknown, d = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function fmt(v: unknown, dp = 2): string {
  return num(v).toFixed(dp);
}

interface Raw {
  kind: BeatKind;
  atMs: number;
  nodes: string[];
  segments: string[];
  caption: string;
  sub?: string;
  event?: CdmasEvent;
  coalesceKey?: string;
}

/** Derive the ordered beat list for a scenario. `overrides` replaces the caption of the
    first beat of a given kind — used to hand-author the hero scenario's narration. */
export function deriveBeats(
  replay: ReplayData,
  overrides?: Partial<Record<BeatKind, string>>,
): Beat[] {
  const events = [...replay.events].sort((a, b) => a.wall_ms - b.wall_ms);
  const segs = replay.topology.segments;
  const raws: Raw[] = [];

  raws.push({
    kind: "intro",
    atMs: 0,
    nodes: [],
    segments: segs,
    caption: `${shortScenarioName(replay.scenario)} — defense fleet online.`,
    sub: `${segs.length} segment${segs.length === 1 ? "" : "s"} monitored · awaiting threats`,
  });

  const seenAttacker = new Set<string>();
  for (const e of events) {
    const seg = e.segment ?? "";
    const sig = e.payload?.signal;

    if (sig === "attack_action" && e.agent_type === "ATK") {
      const node = attackerNodeFor(e);
      if (seenAttacker.has(node)) continue; // one beat per attacker, at first strike
      seenAttacker.add(node);
      raws.push({
        kind: "attack",
        atMs: e.wall_ms,
        nodes: [node, "NETWORK"],
        segments: seg ? [seg] : [],
        caption: `${String(e.payload?.attack_type ?? "Attack")} barrage strikes ${seg || "the network"}.`,
        sub: "hostile traffic floods the perimeter",
        event: e,
        coalesceKey: `attack:${node}`,
      });
    } else if (e.event_type === "ALERT_PUBLISHED") {
      raws.push({
        kind: "detect",
        atMs: e.wall_ms,
        nodes: ["NETWORK", "TMA"],
        segments: seg ? [seg] : [],
        caption: `TMA flags a traffic spike on ${seg}.`,
        sub: `deviation ${fmt(e.payload?.deviation_score, 1)}σ over baseline · alert in ${e.latency_ms ?? 0}ms`,
        event: e,
        coalesceKey: `detect:${seg}`,
      });
    } else if (e.event_type === "THREAT_CLASSIFIED" && e.payload?.reported) {
      const dt = e.decision_trace;
      const bits = [
        dt?.confidence != null ? `confidence ${fmt(dt.confidence)}` : "",
        dt?.novelty != null ? `novelty ${fmt(dt.novelty)}` : "",
        `severity ${fmt(e.payload?.severity)}`,
      ].filter(Boolean);
      raws.push({
        kind: "classify",
        atMs: e.wall_ms,
        nodes: ["TMA", "ACA"],
        segments: seg ? [seg] : [],
        caption: `ACA confirms ${String(e.payload?.attack_type ?? "threat")} on ${seg}.`,
        sub: bits.join(" · "),
        event: e,
        coalesceKey: `classify:${seg}`,
      });
    } else if (sig === "correlation") {
      const cs = (e.payload?.segments as string[] | undefined) ?? [];
      raws.push({
        kind: "correlate",
        atMs: e.wall_ms,
        nodes: ["ACA", "TIA", "RCA"],
        segments: cs,
        caption: `TIA correlates simultaneous incidents across ${cs.join(", ") || "segments"}.`,
        sub: "cross-segment threat pattern detected",
        event: e,
        coalesceKey: "correlate",
      });
    } else if (e.event_type === "COALITION_FORMED") {
      const cs = (e.payload?.segments as string[] | undefined) ?? [];
      raws.push({
        kind: "coalition",
        atMs: e.wall_ms,
        nodes: ["TIA", "RCA"],
        segments: cs,
        caption: `Coalition forms across ${cs.join(", ") || "segments"}.`,
        sub: `lead ${e.payload?.lead_rca ?? "RCA"} · coordinated defense`,
        event: e,
        coalesceKey: "coalition",
      });
    } else if (e.event_type === "VOTE_CAST") {
      const approved = !!e.payload?.approved;
      raws.push({
        kind: "vote",
        atMs: e.wall_ms,
        nodes: ["RCA", "ACA"],
        segments: seg ? [seg] : [],
        caption: `Coalition vote — quarantine ${approved ? "PASSED" : "FAILED"}.`,
        sub: `${num(e.payload?.accept_count)}/${num(e.payload?.member_count)} accept`,
        event: e,
        coalesceKey: `vote:${seg}`,
      });
    } else if (e.event_type === "AUCTION_COMPLETED") {
      const granted = (e.payload?.granted as string[] | undefined)?.length ?? 0;
      raws.push({
        kind: "auction",
        atMs: e.wall_ms,
        nodes: ["RAA", "RCA"],
        segments: [],
        caption: "RAA auctions scarce quarantine slots.",
        sub: `${granted}/${num(e.payload?.slots)} bids granted`,
        event: e,
        coalesceKey: "auction",
      });
    } else if (sig === "response") {
      raws.push({
        kind: "respond",
        atMs: e.wall_ms,
        nodes: ["RCA", "RAA"],
        segments: seg ? [seg] : [],
        caption: `RCA applies ${String(e.payload?.action ?? "response")} on ${seg}.`,
        sub: `least-disruptive effective action · ${e.latency_ms ?? 0}ms · proportionality ${fmt(e.payload?.proportionality_score)}`,
        event: e,
        coalesceKey: `respond:${seg}`,
      });
    } else if (e.event_type === "INCIDENT_RESOLVED") {
      raws.push({
        kind: "resolve",
        atMs: e.wall_ms,
        nodes: ["RCA"],
        segments: seg ? [seg] : [],
        caption: `Incident on ${seg} neutralized.`,
        sub: "segment returning to nominal",
        event: e,
        coalesceKey: `resolve:${seg}`,
      });
    }
  }

  const m = replay.metrics;
  raws.push({
    kind: "outro",
    atMs: replay.duration_ms,
    nodes: [],
    segments: segs,
    caption: "Threats contained — provably within spec.",
    sub: `DR ${(num(m.dr) * 100).toFixed(0)}% · MTTR ${num(m.mttr_response_ms).toFixed(0)}ms · Social Welfare ${fmt(m.social_welfare)}`,
  });

  // One beat per logical phase: keep the FIRST occurrence of each keyed moment
  // (e.g. first detect on a segment), collapsing the repeated cycles a recording
  // contains into a walkable narrative. Intro/outro have no key and always stay.
  const kept: Raw[] = [];
  const seen = new Set<string>();
  for (const r of raws) {
    if (r.coalesceKey) {
      if (seen.has(r.coalesceKey)) continue;
      seen.add(r.coalesceKey);
    }
    kept.push(r);
  }

  // The recording often logs the attacker's action after its injected traffic already
  // tripped an alert. Pull each attack beat just ahead of the first detection on its
  // segment so the narrative reads attack -> detect.
  const firstDetect = new Map<string, number>();
  for (const r of kept) {
    if (r.kind === "detect" && r.segments[0] && !firstDetect.has(r.segments[0])) {
      firstDetect.set(r.segments[0], r.atMs);
    }
  }
  for (const r of kept) {
    if (r.kind === "attack" && r.segments[0]) {
      const d = firstDetect.get(r.segments[0]);
      if (d != null) r.atMs = Math.min(r.atMs, d - 1);
    }
  }
  kept.sort((a, b) => a.atMs - b.atMs);

  const usedOverride = new Set<BeatKind>();
  return kept.map((r, i) => {
    let caption = r.caption;
    const override = overrides?.[r.kind];
    if (override && !usedOverride.has(r.kind)) {
      caption = override;
      usedOverride.add(r.kind);
    }
    return {
      id: `${r.kind}-${Math.round(r.atMs)}-${i}`,
      index: i + 1,
      kind: r.kind,
      atMs: r.atMs,
      windowMs: [i > 0 ? kept[i - 1].atMs : r.atMs, r.atMs],
      camera: boundingBox(r.nodes),
      highlight: { nodes: r.nodes, segments: r.segments },
      caption,
      sub: r.sub,
      event: r.event,
    };
  });
}
