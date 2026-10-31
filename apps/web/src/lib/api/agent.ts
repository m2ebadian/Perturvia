import type { Agent, CreateAgentRequest } from "@/features/agents/types";
import { ApiError } from "@/lib/api/api-error";

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

export async function createAgent(data: CreateAgentRequest): Promise<Agent> {
  const response = await fetch("http://api:8000/agents", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    let message = `Failed to create agent: ${response.status}`;

    if (response.status === 422) {
      try {
        const errorData = await response.json();
        const firstMessage = errorData.detail?.[0]?.msg;
        if (typeof firstMessage === "string") {
          message = firstMessage;
        }
      } catch {
        // Body wasn't JSON — keep the generic message
      }
    }

    throw new ApiError(message, response.status);
  }

  const agent = await response.json();

  return agent;
}
