"""Run the repo-analyst agent once against the repo-tools MCP server, traced by Perturvia."""

import argparse
import asyncio
import dataclasses
import os
import random

import perturvia
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from mcp import Client
from perturvia.faults import FaultPolicy
from perturvia.integrations.mcp import traced_tools

from agent import MODEL_NAME, TEMPERATURE, build_agent
from tools import server_params

MAX_STEPS = int(os.getenv("PERTURVIA_MAX_STEPS", "40"))

TASK = (
    "Analyze this repository. Identify its API endpoints, its main dependencies, "
    "and how it is tested. Cite the files that support each finding."
)

SYSTEM_PROMPT = """\
You are a careful software engineer analyzing a code repository through tools.

- Explore before answering. Start with list_files, then use search_text and read_file
  to gather evidence. Keep calling tools until you have enough evidence for every claim.
- Cite the file path behind every finding, e.g. (apps/api/main.py).
- Only state what you saw in a file. If you could not verify something, because a file
  was missing, blocked, truncated, or a tool failed, say so plainly instead of guessing.
- If a tool returns an error, read the message and adjust: try another path, narrow the
  directory, or search instead.
- When you have enough evidence, answer with a structured report and stop calling tools.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for fault in ("error", "timeout", "latency", "malformed", "injection"):
        parser.add_argument(
            f"--{fault}-rate",
            type=float,
            default=0.0,
            metavar="P",
            help=f"chance (0-1) that a tool call gets the {fault} fault",
        )
    parser.add_argument("--seed", type=int, help="seed for a reproducible fault schedule")
    return parser.parse_args()


def fault_policy(args: argparse.Namespace) -> FaultPolicy:
    try:
        return FaultPolicy(
            error_rate=args.error_rate,
            timeout_rate=args.timeout_rate,
            latency_rate=args.latency_rate,
            malformed_rate=args.malformed_rate,
            injection_rate=args.injection_rate,
        )
    except ValueError as exc:
        raise SystemExit(f"Invalid fault rates: {exc}") from exc


async def main(args: argparse.Namespace) -> None:
    policy = fault_policy(args)
    # Always pick a seed, so any run can be reproduced from the seed its trace records.
    seed = args.seed if args.seed is not None else random.randrange(2**53)
    perturvia.init()

    async with Client(server_params()) as client:
        tools = await traced_tools(client, faults=policy, seed=seed)
        agent = build_agent(tools)

        try:
            with perturvia.run(
                task=TASK,
                config={
                    "model": MODEL_NAME,
                    "temperature": TEMPERATURE,
                    "max_steps": MAX_STEPS,
                    "faults": dataclasses.asdict(policy),
                },
                seed=seed,
            ) as run:
                print(f"Trace: {run.trace_id}  Seed: {seed}")
                with perturvia.span("repo-analyst", kind="agent", agent_name="repo-analyst"):
                    result = await agent.ainvoke(
                        {"messages": [SystemMessage(SYSTEM_PROMPT), HumanMessage(TASK)]},
                        config={"recursion_limit": MAX_STEPS},
                    )
                run.final_output = result["messages"][-1].content
        except GraphRecursionError:
            print(f"\nRun failed: the agent exceeded {MAX_STEPS} steps without finishing.")
            return

    print("\n" + run.final_output)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
