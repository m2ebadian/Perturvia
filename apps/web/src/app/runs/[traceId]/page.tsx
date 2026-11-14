import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { SpanTimeline } from "@/features/traces/components/span-timeline";
import { formatDuration, formatUtc, traceDurationMs } from "@/features/traces/format";
import { statusVariant } from "@/features/traces/status";
import { buildSpanTree, flattenTree } from "@/features/traces/tree";
import { getTrace } from "@/lib/api/trace";

export const dynamic = "force-dynamic";

// Any 8-4-4-4-12 hex string. Deliberately not version-specific: the API accepts
// any UUID, and some trace IDs don't carry a standard version digit.
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function TracePage({ params }: PageProps<"/runs/[traceId]">) {
  const { traceId } = await params;
  if (!UUID_PATTERN.test(traceId)) {
    notFound();
  }

  const trace = await getTrace(traceId);
  if (trace === null) {
    notFound();
  }

  const rows = flattenTree(buildSpanTree(trace.spans));
  const durationMs = traceDurationMs(trace.started_at, trace.ended_at);
  const model = typeof trace.config.model === "string" ? trace.config.model : null;

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <Link
        href="/runs"
        className="mb-4 inline-block text-sm text-muted-foreground hover:underline"
      >
        ← Runs
      </Link>
      <header className="mb-8 grid gap-4">
        <div className="flex items-start gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{trace.task}</h1>
          <Badge variant={statusVariant[trace.status]} className="mt-1.5">
            {trace.status}
          </Badge>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-5">
          <div>
            <dt className="text-muted-foreground">Duration</dt>
            <dd className="tabular-nums">
              {durationMs === null ? "—" : formatDuration(durationMs)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Started</dt>
            <dd className="tabular-nums">{formatUtc(trace.started_at)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Model</dt>
            <dd>{model ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Seed</dt>
            <dd className="tabular-nums">{trace.seed ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Spans</dt>
            <dd className="tabular-nums">{trace.spans.length}</dd>
          </div>
        </dl>

        {trace.final_output !== null && (
          <details className="rounded-md border p-3">
            <summary className="cursor-pointer font-medium">Final output</summary>
            <pre className="mt-3 whitespace-pre-wrap text-sm">{trace.final_output}</pre>
          </details>
        )}
      </header>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Timeline</h2>
        {rows.length === 0 ? (
          <p className="text-muted-foreground">No spans recorded for this run.</p>
        ) : (
          <SpanTimeline rows={rows} />
        )}
      </section>
    </main>
  );
}
