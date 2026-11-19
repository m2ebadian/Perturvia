/**
 * Reads the fields the UI shows from a trace's outcome.
 *
 * The outcome is free-form JSON written by perturvia.evaluate() plus any custom checks,
 * so every field is optional and checked at runtime: a missing or mistyped field
 * becomes null instead of breaking the page.
 */

type Json = Record<string, unknown>;

export interface Outcome {
  benchmark: string | null;
  taskSuccess: boolean | null;
  silentFailure: boolean | null;
  endpoints: { recall: number | null; missing: string[]; invented: string[] } | null;
  dependenciesFound: string[] | null;
  unsupportedCitations: string[] | null;
  recovery: { failed: number; recovered: number; rate: number | null } | null;
  toolErrors: { natural: number; injected: number } | null;
  injectionFollowed: boolean | null;
}

function isObject(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asStrings(value: unknown): string[] | null {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : null;
}

function field(value: unknown, key: string): unknown {
  return isObject(value) ? value[key] : undefined;
}

/** The outcome's task_success, or null when there is no outcome or it has none. */
export function taskSuccess(outcome: Json | null): boolean | null {
  return asBoolean(field(outcome, "task_success"));
}

export function parseOutcome(outcome: Json): Outcome {
  const endpoints = outcome.endpoints;
  const recovery = outcome.recovery;
  const toolErrors = outcome.tool_errors;
  const failed = asNumber(field(recovery, "failed"));
  const recovered = asNumber(field(recovery, "recovered"));
  const natural = asNumber(field(toolErrors, "natural"));
  const injected = asNumber(field(toolErrors, "injected"));

  return {
    benchmark: asString(outcome.benchmark),
    taskSuccess: taskSuccess(outcome),
    silentFailure: asBoolean(outcome.silent_failure),
    endpoints: isObject(endpoints)
      ? {
          recall: asNumber(endpoints.recall),
          missing: asStrings(endpoints.missing) ?? [],
          invented: asStrings(endpoints.invented) ?? [],
        }
      : null,
    dependenciesFound: asStrings(field(outcome.dependencies, "found")),
    unsupportedCitations: asStrings(field(outcome.grounding, "unsupported")),
    recovery:
      failed !== null && recovered !== null
        ? { failed, recovered, rate: asNumber(field(recovery, "rate")) }
        : null,
    toolErrors: natural !== null && injected !== null ? { natural, injected } : null,
    injectionFollowed: asBoolean(outcome.injection_followed),
  };
}

/** Formats a 0-1 ratio as "43%", or "—" when it is null (nothing to measure). */
export function formatRate(rate: number | null): string {
  return rate === null ? "—" : `${Math.round(rate * 100)}%`;
}
