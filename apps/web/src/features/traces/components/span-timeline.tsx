import type { ReactNode } from "react";
import { formatDuration } from "@/features/traces/format";
import type { Span, SpanKind } from "@/features/traces/types";

interface SpanTimelineProps {
  rows: { span: Span; depth: number }[];
}

const kindColor: Record<SpanKind, string> = {
  agent: "bg-violet-500",
  llm: "bg-sky-500",
  tool: "bg-amber-500",
};

const ERROR_COLOR = "bg-red-500";
const MIN_BAR_WIDTH_PERCENT = 0.3;

export function SpanTimeline({ rows }: SpanTimelineProps) {
  if (rows.length === 0) {
    return null;
  }

  // Measure from the spans themselves: every timestamp here comes from the
  // agent's clock, so nothing is subtracted across two different machines.
  const starts = rows.map(({ span }) => Date.parse(span.started_at));
  const ends = rows.map(({ span }, i) => starts[i] + span.duration_ms);
  const origin = Math.min(...starts);
  const total = Math.max(Math.max(...ends) - origin, 1);

  return (
    <div className="grid gap-y-1 text-sm">
      {rows.map(({ span, depth }, i) => {
        const left = ((starts[i] - origin) / total) * 100;
        const width = Math.min(
          Math.max((span.duration_ms / total) * 100, MIN_BAR_WIDTH_PERCENT),
          100 - left,
        );
        const isError = span.status === "error";
        const color = isError ? ERROR_COLOR : kindColor[span.kind];
        const indent = `${depth * 1.25}rem`;

        return (
          <details key={span.id} className="group">
            <summary className="grid cursor-pointer list-none grid-cols-[18rem_1fr] items-center gap-4 rounded-sm hover:bg-muted/50 [&::-webkit-details-marker]:hidden">
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className="truncate font-mono"
                  style={{ paddingLeft: indent }}
                  title={span.name}
                >
                  {span.name}
                </span>
                {isError ? (
                  <span className="ml-auto shrink-0 text-xs font-medium text-red-600">
                    {span.error_type ?? "error"}
                  </span>
                ) : (
                  <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                    {span.kind}
                  </span>
                )}
                <span className="w-14 shrink-0 text-right text-xs tabular-nums">
                  {formatDuration(span.duration_ms)}
                </span>
              </div>
              <div className="relative h-5 rounded-sm bg-muted/40">
                <div
                  className={`absolute inset-y-1 rounded-sm ${color}`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  title={`${span.name} · ${formatDuration(span.duration_ms)}`}
                />
              </div>
            </summary>
            <div className="my-2" style={{ marginLeft: indent }}>
              <SpanDetails span={span} />
            </div>
          </details>
        );
      })}
    </div>
  );
}

function SpanDetails({ span }: { span: Span }) {
  const inputTokens = span.attributes["llm.input_tokens"];
  const outputTokens = span.attributes["llm.output_tokens"];
  const hasTokens = typeof inputTokens === "number" || typeof outputTokens === "number";
  const toolArguments = formatArguments(span.attributes["tool.arguments"]);

  return (
    <dl className="grid grid-cols-[8rem_1fr] gap-x-4 gap-y-2 rounded-md border bg-muted/30 p-3 text-xs">
      {span.error_type !== null && (
        <Field label="Error type">
          <span className="font-medium text-red-600">{span.error_type}</span>
        </Field>
      )}
      {hasTokens && (
        <Field label="Tokens">
          <span className="tabular-nums">
            {String(inputTokens ?? "—")} in · {String(outputTokens ?? "—")} out
          </span>
        </Field>
      )}
      {toolArguments !== null && (
        <Field label="Arguments">
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono">{toolArguments}</pre>
        </Field>
      )}
      {span.fault !== null && (
        <Field label="Fault">
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono">
            {JSON.stringify(span.fault, null, 2)}
          </pre>
        </Field>
      )}
      <Field label="Span ID">
        <span className="font-mono text-muted-foreground">{span.id}</span>
      </Field>
    </dl>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0">{children}</dd>
    </>
  );
}

/** tool.arguments arrives as a JSON string; pretty-print it, or show it raw if it isn't JSON. */
function formatArguments(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}
