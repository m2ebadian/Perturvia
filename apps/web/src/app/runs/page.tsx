import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDuration, formatUtc, traceDurationMs } from "@/features/traces/format";
import { statusVariant } from "@/features/traces/status";
import { listTraces } from "@/lib/api/trace";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const traces = await listTraces();

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Runs</h1>
        <p className="text-muted-foreground">Recent agent runs, newest first.</p>
      </header>

      {traces.length === 0 ? (
        <p className="text-muted-foreground">No runs recorded yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Duration</TableHead>
              <TableHead>Started</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {traces.map((trace) => {
              const durationMs = traceDurationMs(trace.started_at, trace.ended_at);
              return (
                <TableRow key={trace.id}>
                  <TableCell className="max-w-md truncate">
                    <Link href={`/runs/${trace.id}`} className="hover:underline">
                      {trace.task}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[trace.status]}>{trace.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {durationMs === null ? "—" : formatDuration(durationMs)}
                  </TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {formatUtc(trace.started_at)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </main>
  );
}
