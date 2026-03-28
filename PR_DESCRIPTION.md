# PR Title:
Add Docker Compose setup for containerized local development (#75)

# PR Description (paste this into GitHub):

## Summary

Adds Docker Compose support for running the chatbot API backend in a containerized environment. This addresses issue #75 by providing a one-command setup that eliminates manual environment configuration.

## What's Included

- `Dockerfile.chatbot` - Multi-stage Dockerfile for the Python backend with system dependencies for llama-cpp-python
- `docker-compose.yml` - Default configuration running in lite mode (no LLM model required)
- `docker-compose.full.yml` - Override file for full mode with local LLM support
- `.dockerignore` - Keeps the Docker context clean and builds fast
- `docs/docker-setup.md` - Documentation covering quick start, full mode, and troubleshooting

## How to Test

```bash
# Build and start (lite mode)
docker compose up --build

# Verify the API is running
curl -X POST http://localhost:8000/api/chatbot/sessions

# Check health endpoint
curl http://localhost:8000/health
```

## Design Decisions

- **Lite mode by default.** Most contributors don't need the 4GB LLM model for their work. The default setup skips model loading (via `PYTEST_VERSION=1`) so the container starts quickly.
- **Separate override file for full mode.** Rather than complicating the default compose file with conditional logic, a clean override file (`docker-compose.full.yml`) handles full LLM mode.
- **Source mounted as volume.** The `chatbot-core/` directory is mounted into the container so code changes are reflected immediately via uvicorn's reload. No rebuild needed for Python changes.
- **CPU requirements by default.** Uses `requirements-cpu.txt` in the Dockerfile to avoid NVIDIA dependency issues. The full-mode override switches to `requirements.txt`.
- **Session persistence.** A named Docker volume (`chatbot-sessions`) persists chat sessions across container restarts.
- **Jenkins service commented out.** Included as a ready-to-uncomment block for contributors who want a local Jenkins instance for integration testing.

## Checklist

- [x] Builds successfully with `docker compose up --build`
- [x] API responds on `http://localhost:8000`
- [x] Health check passes
- [x] Live reload works (edit Python file, see change reflected)
- [x] Documentation added

Closes #75
