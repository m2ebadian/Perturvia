import { createAgent } from "@/lib/api/agent";
import type { CreateAgentRequest } from "@/features/agents/types";
import { ApiError } from "@/lib/api/api-error";

export async function POST(request: Request) {
  let data: CreateAgentRequest;

  try {
    data = await request.json();
  } catch {
    return Response.json({ error: "Request body must be valid JSON" }, { status: 400 });
  }

  try {
    const agent = await createAgent(data);
    return new Response(JSON.stringify(agent), {
      status: 201,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return Response.json({ error: error.message }, { status: error.status });
    }

    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
