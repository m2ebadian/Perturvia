import type { Trace, TraceDetail } from "@/features/traces/types";
import { ApiError } from "@/lib/api/api-error";
import { API_URL } from "@/lib/api/config";

export async function listTraces(params?: { agentId?: string; limit?: number }): Promise<Trace[]> {
  const query = new URLSearchParams();
  if (params?.agentId !== undefined) {
    query.set("agent_id", params.agentId);
  }
  if (params?.limit !== undefined) {
    query.set("limit", String(params.limit));
  }

  const queryString = query.toString();
  const url = `${API_URL}/v1/traces${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new ApiError(`Failed to fetch traces: ${response.status}`, response.status);
  }
  const traces = await response.json();

  return traces;
}

export async function getTrace(traceId: string): Promise<TraceDetail | null> {
  const response = await fetch(`${API_URL}/v1/traces/${encodeURIComponent(traceId)}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new ApiError(`Failed to fetch trace: ${response.status}`, response.status);
  }
  const trace = await response.json();

  return trace;
}
