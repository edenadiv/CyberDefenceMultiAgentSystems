export interface DecisionTrace {
  inputs: Record<string, unknown>;
  plan_selected: string;
  reasoning: string;
  action: string;
  // Structured decision internals (Phase 1 backend enrichment) — present on
  // THREAT_CLASSIFIED (classifier) and VOTE_CAST (per-voter) events.
  confidence?: number | null;
  novelty?: number | null;
  features?: number[] | null;
  feature_names?: string[] | null;
  votes?: Record<string, string> | null; // voter_id -> ACCEPT/REJECT
  vote_rationale?: Record<string, string> | null;
}

/** A representative sampled packet for the war-room (sibling to events). */
export interface SampledPacket {
  src_ip: string;
  dst_ip: string;
  port: number;
  protocol: string;
  pkt_size: number;
  freq: number;
  ts_ms: number;
  kind: "benign" | "ddos" | "port_scan" | "lateral" | "zero_day";
  segment: string;
  alert_ms: number | null; // wall_ms of the alert this burst triggered
}

export interface CdmasEvent {
  event_id: string;
  lamport_ts: number;
  wall_ms: number;
  event_type: string;
  timestamp: string;
  agent_id: string;
  agent_type: string;
  segment: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload: Record<string, any>;
  latency_ms: number | null;
  decision_trace: DecisionTrace | null;
}

export interface Metrics {
  dr: number;
  fpr: number;
  mttr_alert_ms: number;
  mttr_response_ms: number;
  availability: number;
  resource_overhead: number;
  social_welfare: number;
  attacker_utility: number;
  coalition_ms: number | null;
  evasion_rate: number | null;
  concurrent_incidents: number;
}

export interface TopologyInfo {
  segments: string[];
  adjacency: Record<string, string[]>;
}

export interface ReplayData {
  scenario: string;
  duration_ms: number;
  topology: TopologyInfo;
  events: CdmasEvent[];
  metrics: Metrics;
  packets?: SampledPacket[];
  messages?: unknown[];
}

export interface Constraint {
  fr_id: string;
  status: "PASS" | "FAIL" | "NA";
  description: string;
  observed: string;
}

export interface ScenarioValidation {
  name: string;
  passed: boolean;
  social_welfare: number;
  criteria: Record<string, boolean>;
  constraints: Constraint[];
}

/** The bundled export: one recording per scenario + the validation summary. */
export interface ExportBundle {
  replays: ReplayData[];
  validation: ScenarioValidation[];
}

/** View over the bundle for the active scenario; what panels consume. */
export interface ExportData {
  topology: TopologyInfo;
  replay: ReplayData;
  validation: ScenarioValidation[];
}
