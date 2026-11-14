/** Formats a duration in milliseconds as "850 ms", "12.3 s" or "4m 05s". */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)} ms`;
  }
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(1)} s`;
  }
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

/**
 * Formats an ISO timestamp as "2026-11-13 14:05:09 UTC".
 * Always UTC, so the output doesn't depend on the server's or browser's time zone.
 */
export function formatUtc(iso: string): string {
  return `${new Date(iso).toISOString().slice(0, 19).replace("T", " ")} UTC`;
}

/** Wall-clock duration of a trace, or null while it is still running. */
export function traceDurationMs(startedAt: string, endedAt: string | null): number | null {
  if (endedAt === null) {
    return null;
  }
  return new Date(endedAt).getTime() - new Date(startedAt).getTime();
}
