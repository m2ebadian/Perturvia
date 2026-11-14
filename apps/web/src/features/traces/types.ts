export type TraceStatus = "running" | "completed" | "failed";
export type SpanKind = "agent" | "llm" | "tool";
export type SpanStatus = "ok" | "error";

export interface Trace {
  id: string;
  agent_id: string | null;
  task: string;
  status: TraceStatus;
  config: Record<string, unknown>;
  seed: number | null;
  experiment_id: string | null;
  trial_number: number | null;
  final_output: string | null;
  outcome: Record<string, unknown> | null;
  started_at: string;
  ended_at: string | null;
}

export interface Span {
  id: string;
  trace_id: string;
  parent_span_id: string | null;
  sequence: number;
  kind: SpanKind;
  name: string;
  agent_name: string | null;
  status: SpanStatus;
  error_type: string | null;
  started_at: string;
  duration_ms: number;
  attributes: Record<string, unknown>;
  fault: Record<string, unknown> | null;
  retry_of_span_id: string | null;
  input_span_ids: string[];
  created_at: string;
}

export interface TraceDetail extends Trace {
  spans: Span[];
}
