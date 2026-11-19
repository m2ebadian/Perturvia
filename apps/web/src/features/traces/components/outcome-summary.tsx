import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { formatRate, type Outcome } from "@/features/traces/outcome";

function YesNo({ value, badWhen }: { value: boolean | null; badWhen: boolean }) {
  if (value === null) {
    return <>—</>;
  }
  return (
    <Badge variant={value === badWhen ? "destructive" : "secondary"}>{value ? "yes" : "no"}</Badge>
  );
}

function List({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <span className="text-muted-foreground">none</span>;
  }
  return <span className="font-mono text-xs">{items.join(", ")}</span>;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[12rem_1fr] gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function OutcomeSummary({ outcome }: { outcome: Outcome }) {
  const { endpoints, recovery, toolErrors } = outcome;

  return (
    <div className="grid gap-3">
      {outcome.silentFailure === true && (
        <p
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm font-medium text-destructive"
        >
          Silent failure: the run completed and the task failed, but the report did not disclose a
          problem.
        </p>
      )}

      <dl className="grid gap-2 text-sm">
        {outcome.benchmark !== null && <Row label="Benchmark">{outcome.benchmark}</Row>}
        <Row label="Task success">
          <YesNo value={outcome.taskSuccess} badWhen={false} />
        </Row>
        <Row label="Silent failure">
          <YesNo value={outcome.silentFailure} badWhen={true} />
        </Row>
        {endpoints !== null && (
          <>
            <Row label="Endpoint recall">{formatRate(endpoints.recall)}</Row>
            <Row label="Missing endpoints">
              <List items={endpoints.missing} />
            </Row>
            <Row label="Invented endpoints">
              <List items={endpoints.invented} />
            </Row>
          </>
        )}
        {outcome.dependenciesFound !== null && (
          <Row label="Dependencies found">
            <List items={outcome.dependenciesFound} />
          </Row>
        )}
        {outcome.unsupportedCitations !== null && (
          <Row label="Unsupported citations">
            <List items={outcome.unsupportedCitations} />
          </Row>
        )}
        {recovery !== null && (
          <Row label="Recovery">
            <span className="tabular-nums">
              {recovery.recovered}/{recovery.failed} recovered ({formatRate(recovery.rate)})
            </span>
          </Row>
        )}
        {toolErrors !== null && (
          <Row label="Tool errors">
            <span className="tabular-nums">
              {toolErrors.natural} natural, {toolErrors.injected} injected
            </span>
          </Row>
        )}
        {outcome.injectionFollowed !== null && (
          <Row label="Injection followed">
            <YesNo value={outcome.injectionFollowed} badWhen={true} />
          </Row>
        )}
      </dl>
    </div>
  );
}
