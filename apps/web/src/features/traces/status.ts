import type { TraceStatus } from "@/features/traces/types";

export const statusVariant: Record<TraceStatus, "outline" | "secondary" | "destructive"> = {
  running: "outline",
  completed: "secondary",
  failed: "destructive",
};
