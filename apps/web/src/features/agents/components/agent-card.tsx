import type { Agent } from "@/features/agents/types";
import {Card, CardHeader, CardTitle, CardDescription} from "@/components/ui/card"

interface AgentCardProps {
  agent: Agent;
}


export function AgentCard({ agent }: AgentCardProps) {

  return (
    <Card>
      <CardHeader>
        <CardTitle>{agent.name}</CardTitle>
        <CardDescription>{agent.description ?? "No description available"}</CardDescription>
      </CardHeader>
    </Card>
  )

}
