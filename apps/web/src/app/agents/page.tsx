import { getAgents } from "@/lib/api/agent";
import { AgentList } from "@/features/agents/components/agent-list";

export default async function AgentsPage() {
  const agents = await getAgents();
  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Agent Registry</h1>
        <p className="text-muted-foreground">
          Welcome to the Agent Registry. Manage and view your registered AI agents.
        </p>
        <p className="text-muted-foreground">
          {agents.length === 1 ? "There is 1 agent" : `There are ${agents.length} agents`}{" "}
          registered.
        </p>
      </header>
      <AgentList agents={agents} />
    </main>
  );
}
