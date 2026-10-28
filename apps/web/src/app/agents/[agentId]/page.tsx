import { getAgent } from "@/lib/api/agent";



export default async function AgentPage({params} : PageProps<"/agents/[agentId]">){

  const {agentId} = await params;
  const agent = await getAgent(agentId);
  return (
    <main>
      <h1>Agent {agentId}</h1>
      <p>Name: {agent.name}</p>
      <p>Description: {agent.description}</p>
    </main>
  )


}
