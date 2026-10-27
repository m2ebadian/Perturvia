# Perturvia

**An Open-Source AI Agent Reliability Engineering Platform**

*Observe. Break. Predict. Improve.*

Perturvia is an open-source platform for testing, monitoring, and improving the reliability of AI agents. Built around the Model Context Protocol (MCP), it aims to help developers understand how agents behave, identify weaknesses, reproduce failures, and evaluate how well their systems recover from unexpected conditions.

The long-term goal is to build a flexible reliability and security layer for agentic AI systems, combining execution observability, controlled fault injection, automated testing, and machine learning.

Rather than focusing on a single agent framework or industry, Perturvia is being designed as extensible infrastructure that can support different models, tools, and applications.

## What We're Building

Perturvia's planned capabilities include:

- **Mission Control** — Monitor agent executions, performance, failures, and reliability trends through a centralized dashboard.
- **Workflow Studio** — Visualize agent workflows, tool dependencies, and execution paths.
- **Execution Inspector** — Explore detailed execution traces, MCP interactions, retries, errors, and agent behavior.
- **MCP Reliability Gateway** — Observe and intercept tool interactions, introduce controlled failures, and support security policies.
- **MCP Reliability Twin** — Reproduce execution conditions and replay interactions for debugging and controlled experimentation.
- **Chaos Laboratory** — Run repeatable fault-injection experiments to evaluate agent resilience under different conditions.
- **Reliability Intelligence** — Benchmark agent behavior, compare execution outcomes, and evaluate recovery strategies.
- **Predictive Intelligence** — Apply machine learning to failure prediction, anomaly detection, and reliability analysis.

Future development will explore automated vulnerability discovery, counterfactual execution analysis, and adaptive resilience mechanisms.

Perturvia also aims to expose its own MCP server, allowing compatible AI assistants to retrieve reliability insights and initiate authorized testing workflows.

## Technology

Perturvia is being developed as a modular, full-stack platform with an emphasis on extensibility, reproducible experimentation, and production-oriented engineering. The following represents the planned technology stack as development progresses.

| Layer | Technologies |
|---|---|
| **Frontend** | TypeScript, React, Next.js, Tailwind CSS, shadcn/ui, React Flow, TanStack Query, Zustand, Recharts |
| **Backend** | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| **Data & Processing** | PostgreSQL, Supabase (managed hosting), Redis, Python background workers |
| **Agentic AI & MCP** | LangGraph, LangChain, Official MCP SDK, OpenTelemetry |
| **LLMs & Inference** | Qwen (initial model), Ollama, OpenAI API, vLLM |
| **Machine Learning & MLOps** | NumPy, Pandas, SciPy, scikit-learn, XGBoost, MLflow |
| **Testing** | pytest, HTTPX, Ruff, Vitest, React Testing Library, Playwright |
| **DevOps & Deployment** | Git, GitHub Actions, Docker, Docker Compose, AWS, Vercel |

*Planned stack. Technologies will be introduced incrementally as development progresses.*

*Potential future extensions: Apache Kafka, Apache Spark, Kubernetes, and graph-based machine learning.*

The initial architecture follows a modular monolith approach, with separate background processing where needed. Perturvia is designed to remain model-agnostic and framework-independent, allowing support for additional LLM providers, agent frameworks, and MCP integrations over time.

## Project Status

**Early Development — Phase 1: Architecture & System Design**

The initial development environment, frontend and backend foundations, Docker configuration, and CI workflows are in place.

Current development focuses on designing the core execution, experimentation, and MCP integration architecture before implementing the first end-to-end reliability testing workflows.

The initial target is a **90-day MVP**, followed by incremental development toward a broader open-source platform.

## Long-Term Vision

AI agents are increasingly interacting with external tools, APIs, databases, and critical systems. As these systems become more autonomous, understanding their failure modes and ensuring reliable behavior becomes increasingly important.

Perturvia aims to make agent reliability something developers can systematically observe, test, measure, and improve.

The broader ambition is to create reusable infrastructure that supports reliable and secure agentic applications across industries, from software development and cybersecurity to healthcare and enterprise automation.

---

**License:** Apache 2.0