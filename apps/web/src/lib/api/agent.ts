import type { Agent } from "@/features/agents/types";

export async function getAgents(): Promise<Agent[]> {
  const response = await fetch("http://api:8000/agents");
  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.status}`);
  }
  const agents = await response.json();

  return agents;
}


export async function getAgent(agentId: string): Promise<Agent> {
  const response = await fetch(`http://api:8000/agents/${agentId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch agent: ${response.status}`);
  }
  const agent = await response.json();

  return agent;
}
