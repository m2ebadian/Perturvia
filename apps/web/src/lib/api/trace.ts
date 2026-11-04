import type { ToolTrace } from "@/features/traces/types";
import { ApiError } from "@/lib/api/api-error";

export async function getTraces(runId: string): Promise<ToolTrace[]> {
  const response = await fetch(
    `http://api:8000/traces?run_id=${encodeURIComponent(runId)}`,
    { cache: "no-store" },
  );
  if (!response.ok) {
    throw new ApiError(
      `Failed to fetch traces: ${response.status}`,
      response.status,
    );
  }
  const traces = await response.json();

  return traces;
}
