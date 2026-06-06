export interface DecisionTrace {
  inputs: Record<string, unknown>;
  plan_selected: string;
  reasoning: string;
  action: string;
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

export interface ReplayData {
  scenario: string;
  duration_ms: number;
  events: CdmasEvent[];
  metrics: Metrics;
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

export interface ExportData {
  topology: { segments: string[]; adjacency: Record<string, string[]> };
  replay: ReplayData;
  validation: ScenarioValidation[];
}
