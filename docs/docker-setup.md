# Docker Setup

This guide explains how to run the chatbot API using Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)

## Quick Start (Lite Mode)

Lite mode runs the API without loading a local LLM model. This is suitable for most development work including API changes, data pipeline work, and testing.

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

Verify it's running:
```bash
curl -X POST http://localhost:8000/api/chatbot/sessions
```

**What works in lite mode:** All API endpoints, session management, context search, data pipeline.

**What doesn't work:** Actual chat completions (no model loaded).

## Full Mode (With Local LLM)

To run with a local LLM for complete chat functionality:

1. Download the Mistral 7B model:
   - Go to https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
   - Download `mistral-7b-instruct-v0.2.Q4_K_M.gguf`
   - Place it in `chatbot-core/api/models/mistral/`

2. Start with the full-mode override:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.full.yml up --build
   ```

## Adding a Local Jenkins Instance

If you want to test the plugin alongside a local Jenkins server, uncomment the `jenkins` service block in `docker-compose.yml`, then run:

```bash
docker compose up --build
```

Jenkins will be available at `http://localhost:8080`.

## Common Commands

```bash
# Start in background
docker compose up -d --build

# View logs
docker compose logs -f chatbot-api

# Stop all services
docker compose down

# Stop and remove volumes (clears session data)
docker compose down -v

# Rebuild after dependency changes
docker compose build --no-cache chatbot-api
```

## Development Workflow

The `chatbot-core/` directory is mounted as a volume, so code changes are reflected immediately thanks to uvicorn's `--reload` flag. You do not need to rebuild the container after editing Python source files.

If you change `requirements.txt` or `requirements-cpu.txt`, rebuild the container:
```bash
docker compose build --no-cache chatbot-api
```

## Troubleshooting

**Container exits immediately:**
Check logs with `docker compose logs chatbot-api`. Common causes include missing Python dependencies or port conflicts.

**Port 8000 already in use:**
Either stop the process using port 8000, or change the port mapping in `docker-compose.yml` (e.g., `"8001:8000"`).

**Build fails on llama-cpp-python:**
The default setup uses `requirements-cpu.txt` which avoids GPU dependencies. If you need GPU support, ensure your system has the NVIDIA Container Toolkit installed.
