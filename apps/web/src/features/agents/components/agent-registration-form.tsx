"use client";

import type { CreateAgentRequest } from "@/features/agents/types";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function AgentRegistrationForm() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting === true) {
      return;
    }
    setIsSubmitting(true);
    setError(null);

    let succeeded = false;

    try {
      const formData = new FormData(event.currentTarget);
      const name = (formData.get("name") as string).trim();
      if (name.length === 0) {
        setError("Agent name is required.");
        return;
      }
      const description = (formData.get("description") as string).trim();

      const data: CreateAgentRequest = {
        name: name,
        description: description || undefined,
      };

      const response = await fetch("/api/agents", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setError(errorData.error || "Registration failed. Please try again.");
        return;
      }
      const agent = await response.json();
      succeeded = true;
      router.push(`/agents/${agent.id}`);
    } catch {
      setError("Registration failed. Please try again.");
    } finally {
      if (!succeeded) {
        setIsSubmitting(false);
      }
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="name">Name</label>
      <input type="text" id="name" name="name" required />
      <label htmlFor="description">Description</label>
      <textarea id="description" name="description"></textarea>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Registering..." : "Register Agent"}
      </button>
    </form>
  );
}
