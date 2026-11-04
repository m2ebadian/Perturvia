export interface ToolTrace {
  id: string;
  run_id: string;
  agent_id: string | null;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown> | unknown[] | null;
  status: "success" | "tool_error" | "client_exception";
  error_message: string | null;
  duration_ms: number;
  started_at: string;
  created_at: string;
  fault_injection: Record<string, unknown> | null;
}
