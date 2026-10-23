# Perturvia

**An MCP-Native AI Agent Reliability Engineering Platform**

*Observe. Break. Predict. Improve.*

Perturvia is a full-stack platform designed to help developers monitor, test, and improve the reliability of AI agent systems. It combines execution tracing, Model Context Protocol (MCP) integration, controlled fault injection, reliability analysis, and machine learning into a unified developer experience.

> **Status:** Early Development | **Initial Goal:** 90-Day MVP

## Core Features (Planned)

- **Mission Control:** Monitor agent executions, latency, failures, and performance metrics.
- **Workflow Studio:** Visualize agent relationships, tool dependencies, and execution paths.
- **Execution Inspector:** Examine detailed traces, MCP interactions, retries, and errors.
- **MCP Reliability Gateway:** Instrument MCP interactions and introduce controlled test failures.
- **MCP Reliability Twin:** Reproduce MCP interaction conditions in isolated testing environments.
- **Chaos Laboratory:** Run repeatable fault-injection experiments to evaluate agent resilience.
- **Reliability Intelligence:** Generate reliability profiles and compare workflow versions to measure improvements.
- **Predictive Intelligence:** Apply machine learning to failure prediction and anomaly detection.

Perturvia will also expose its own MCP server, allowing compatible AI coding assistants to access reliability insights and initiate authorized experiments.

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | TypeScript, React, Next.js, Tailwind CSS, shadcn/ui, React Flow, TanStack Query, Zustand, Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Data & Processing | PostgreSQL, Redis, Python background workers |
| Agentic AI & MCP | LangGraph, LangChain, Official MCP SDK, OpenTelemetry |
| Machine Learning | NumPy, Pandas, SciPy, scikit-learn, XGBoost, MLflow |
| Testing | Pytest, HTTPX, Vitest, React Testing Library, Playwright |
| DevOps | Git, GitHub Actions, Docker, Docker Compose, AWS, Vercel |

*Potential future extensions: Apache Kafka, Apache Spark, and graph-based machine learning.*

## Development Approach

Perturvia follows a modular monolith architecture with separate background processing. Development prioritizes complete frontend-to-backend features, reproducible experiments, automated testing, and CI/CD from the beginning.

The project is currently in the environment setup and repository initialization stage.

---

**Goal:** Make AI agent reliability measurable, testable, and continuously improvable.