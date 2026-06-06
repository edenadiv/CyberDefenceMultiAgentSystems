/* Replay engine: derive the command-center state at any point in a recorded run.
   This is what makes the dashboard "play" a scenario over time. */
import type { CdmasEvent } from "./types";

export type SegStatus = "normal" | "under_attack" | "mitigating" | "quarantined";

export interface SegmentState {
  id: string;
  status: SegStatus;
}

export interface AlertItem {
  id: string;
  ts: number;
  level: "critical" | "suspicious" | "info";
  message: string;
  meta: string;
}

export interface FlowEdge {
  from: string; // agent type
  to: string; // agent type
  kind: string;
}

export interface Coalition {
  members: string[];
  segments: string[];
}

export interface DerivedState {
  segments: Record<string, SegmentState>;
  alerts: AlertItem[];
  flows: FlowEdge[];
  coalitions: Coalition[];
  overhead: number;
  counts: { alerts: number; classified: number; responses: number; votes: number };
}

const FLOW_WINDOW_MS = 350;

function levelFor(severity: number, classification?: string): "critical" | "suspicious" | "info" {
  if (classification === "CONFIRMED_THREAT" || severity >= 0.7) return "critical";
  if (classification === "SUSPICIOUS" || severity >= 0.4) return "suspicious";
  return "info";
}

function edgesFor(e: CdmasEvent): FlowEdge[] {
  const sig = e.payload?.signal;
  switch (e.event_type) {
    case "ALERT_PUBLISHED":
      return [{ from: "TMA", to: "ACA", kind: "alert" }];
    case "THREAT_CLASSIFIED":
      return [
        { from: "ACA", to: "RCA", kind: "report" },
        { from: "ACA", to: "TIA", kind: "report" },
      ];
    case "COALITION_FORMED":
      return [{ from: "TIA", to: "RCA", kind: "coalition" }];
    case "VOTE_CAST":
      return [{ from: "RCA", to: "ACA", kind: "vote" }];
    case "AUCTION_COMPLETED":
      return [{ from: "RAA", to: "RCA", kind: "grant" }];
    case "ACTION_EXECUTED":
      if (sig === "response") return [{ from: "RCA", to: "RAA", kind: "mitigate" }];
      if (sig === "correlation") return [{ from: "TIA", to: "RCA", kind: "correlate" }];
      return [];
    default:
      return [];
  }
}

export function deriveState(events: CdmasEvent[], t: number, allSegments: string[]): DerivedState {
  const segments: Record<string, SegmentState> = {};
  for (const s of allSegments) segments[s] = { id: s, status: "normal" };

  const alerts: AlertItem[] = [];
  const coalitions: Coalition[] = [];
  let overhead = 0;
  const counts = { alerts: 0, classified: 0, responses: 0, votes: 0 };
  const flows: FlowEdge[] = [];
  const seenFlow = new Set<string>();

  for (const e of events) {
    if (e.wall_ms > t) break;
    const seg = e.segment;
    const sig = e.payload?.signal;

    if (e.event_type === "ALERT_PUBLISHED" && seg) {
      counts.alerts++;
      if (segments[seg] && segments[seg].status === "normal") segments[seg].status = "under_attack";
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: "suspicious",
        message: `Traffic anomaly on ${seg}`,
        meta: `TMA · deviation ${Number(e.payload.deviation_score ?? 0).toFixed(1)} sigma · ${e.latency_ms ?? 0}ms`,
      });
    } else if (e.event_type === "THREAT_CLASSIFIED" && e.payload.reported) {
      counts.classified++;
      const lvl = levelFor(Number(e.payload.severity ?? 0), e.payload.classification);
      if (seg && segments[seg] && lvl === "critical") segments[seg].status = "under_attack";
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: lvl,
        message: `${e.payload.attack_type ?? "THREAT"} classified on ${seg}`,
        meta: `ACA · sev ${Number(e.payload.severity ?? 0).toFixed(2)} · ${e.payload.classification}`,
      });
    } else if (e.event_type === "ACTION_EXECUTED" && sig === "response" && seg) {
      counts.responses++;
      const action = String(e.payload.action ?? "");
      if (segments[seg]) {
        segments[seg].status = action === "QUARANTINE" ? "quarantined" : "mitigating";
      }
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: "info",
        message: `${action} applied on ${seg}`,
        meta: `RCA · ${e.latency_ms ?? 0}ms · proportionality ${Number(e.payload.proportionality_score ?? 0).toFixed(2)}`,
      });
    } else if (e.event_type === "VOTE_CAST") {
      counts.votes++;
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: e.payload.approved ? "info" : "suspicious",
        message: `Quarantine vote ${e.payload.approved ? "PASSED" : "FAILED"}`,
        meta: `RCA · ${e.payload.accept_count}/${e.payload.member_count} approve`,
      });
    } else if (e.event_type === "COALITION_FORMED") {
      coalitions.length = 0;
      coalitions.push({
        members: (e.payload.members as string[]) ?? [],
        segments: (e.payload.segments as string[]) ?? [],
      });
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: "info",
        message: `Coalition formed across ${(e.payload.segments as string[])?.join(", ")}`,
        meta: `TIA · lead ${e.payload.lead_rca}`,
      });
    } else if (e.event_type === "AGENT_FAILED") {
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: "critical",
        message: `Agent failure: ${e.payload.failed_agent}`,
        meta: `TIA · reassigning coverage`,
      });
    } else if (sig === "coverage_reassigned" && seg) {
      alerts.unshift({
        id: e.event_id,
        ts: e.wall_ms,
        level: "info",
        message: `Coverage reassigned on ${seg}`,
        meta: `failover · ${e.payload.new_owner}`,
      });
    }
    if (sig === "overhead") overhead = Number(e.payload.overhead ?? overhead);

    if (e.wall_ms >= t - FLOW_WINDOW_MS) {
      for (const edge of edgesFor(e)) {
        const key = `${edge.from}-${edge.to}-${edge.kind}`;
        if (!seenFlow.has(key)) {
          seenFlow.add(key);
          flows.push(edge);
        }
      }
    }
  }

  return { segments, alerts: alerts.slice(0, 40), flows, coalitions, overhead, counts };
}
