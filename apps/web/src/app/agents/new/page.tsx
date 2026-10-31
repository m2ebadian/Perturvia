import { AgentRegistrationForm } from "@/features/agents/components/agent-registration-form";

export default function NewAgentPage() {
  return (
    <main>
      <h1>Register Agent</h1>
      <p>Fill in the details below to register a new agent.</p>

      <AgentRegistrationForm />
    </main>
  );
}
