import { getTraces } from "@/lib/api/trace";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default async function RunPage({ params }: PageProps<"/runs/[runId]">) {
  const { runId } = await params;
  const traces = await getTraces(runId);
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Execution Inspector</h1>
        <p className="text-muted-foreground">Run ID: {runId}</p>
        <p className="text-muted-foreground">
          {traces.length === 1 ? "1 tool call" : `${traces.length} tool calls`}
        </p>
      </header>
      {traces.length === 0 ? (
        <p>No traces recorded for this run.</p>
      ) : (
        <ol className="grid gap-4">
          {traces.map((trace) => (
            <li key={trace.id}>
              <Card>
                <CardHeader>
                  <CardTitle>{trace.tool_name}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3">
                  <div className="grid gap-1">
                    <p>Status: {trace.status}</p>
                    <p>Duration: {trace.duration_ms.toFixed(2)} ms</p>
                    <p>
                      Started: <time dateTime={trace.started_at}>{trace.started_at}</time>
                    </p>
                  </div>
                  {trace.error_message && (
                    <div className="grid gap-1">
                      <h2 className="font-medium">Error message</h2>
                      <p className="text-destructive">{trace.error_message}</p>
                    </div>
                  )}
                  <div className="grid gap-1">
                    <h2 className="font-medium">Arguments</h2>
                    <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                      {JSON.stringify(trace.arguments, null, 2)}
                    </pre>
                  </div>
                  <div className="grid gap-1">
                    <h2 className="font-medium">Result</h2>
                    {trace.result === null ? (
                      <p className="text-muted-foreground">No result returned.</p>
                    ) : (
                      <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                        {JSON.stringify(trace.result, null, 2)}
                      </pre>
                    )}
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
