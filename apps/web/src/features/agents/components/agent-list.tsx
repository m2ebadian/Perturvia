import type { Agent } from "@/features/agents/types";
import { AgentCard } from "@/features/agents/components/agent-card";
import Link from "next/link";

interface AgentListProps {
  agents: Agent[];
}

export function AgentList({ agents }: AgentListProps) {
  return agents.length === 0 ? (
    <p>Nothing to display</p>
  ) : (
    <ul className="grid gap-4 md:grid-cols-2">
      {agents.map((agent) => (
        <li key={agent.id}>
          <Link className="block transition-transform hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-ring rounded-xl" href={`/agents/${agent.id}`}>
            <AgentCard agent={agent} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
