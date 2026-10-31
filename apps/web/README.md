# Perturvia Web

Next.js frontend for Perturvia.

The application currently provides an interface for registering and viewing agents. Additional monitoring and execution-inspection features are under development.

## Stack

Next.js, React, TypeScript, and Tailwind CSS.

## Running locally

From the repository root:

```bash
docker compose up -d --build
```

Open `http://localhost:3000`.

The frontend communicates with the FastAPI backend, which runs on port 8000.

## Development

To work on the frontend separately:

```bash
cd apps/web
npm ci
npm run dev
```

Run `npm run lint` to check for linting issues.
