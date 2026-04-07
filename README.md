# Resources AI Chatbot Plugin

## Introduction

Beginners often struggle to take their first steps with Jenkins’ documentation and available resources. To address this challenge, this plugin integrates an AI-powered assistant directly into the Jenkins interface. It offers quick, intuitive support to users of all experience levels through a simple conversational UI.

The plugin is designed to reduce the learning curve for newcomers while also improving accessibility and productivity for experienced users.

### Agentic Architecture Upgrade
The backend has been upgraded from a simple RAG application to a **Context-Aware Agentic Architecture**. It utilizes multiple agents to fetch and synthesize data:
- **Agent Orchestrator (Agent 1)**: Coordinates the interactions between the user and other specialized agents.
- **Documenting Agent (Agent 2)**: Uses RAG (Retrieval-Augmented Generation) to search official Jenkins documentation, plugin details, and community threads.
- **Log Analyzing Agent (Agent 3)**: Connects to the Jenkins API to retrieve runtime data (such as failed build logs) and provides targeted troubleshooting analysis using an LLM.

This architecture enables the chatbot to combine static documentation results with dynamic runtime analysis for a more comprehensive assistant experience.

### Updated Roadmap: Agentic Orchestration

With the infrastructure stabilized, the project is moving into the Three-Agent Orchestration phase:

| Agent | Responsibility | Status |
|---|---|---|
| **Agent 1: Orchestrator** | Routing logic and query classification | In Progress (TDD) |
| **Agent 2: Documenting** | RAG-based Jenkins documentation retrieval | Planned |
| **Agent 3: Log Analysis** | Real-time diagnostic feedback for build failures | Planned |

### Recent Architectural Migration & Optimization

During the development of the Agentic Orchestrator, a critical subsystem bottleneck was identified and resolved. This migration was essential for maintaining build integrity and enabling a professional development cycle.

**The Challenge: 9P Protocol I/O Deadlocks**

While developing in a Windows-interoperable environment (`/mnt/x/`), the Maven build process for the Jenkins HPI package encountered severe synchronization failures.
- **Symptoms:** Intermittent `Unknown packaging: hpi` errors and "No space left on device" false-positives.
- **Root Cause:** High-frequency metadata requests during the Maven lifecycle triggered deadlocks in the WSL2 9P Subsystem bridge (`p9io.cpp:258`), preventing the Maven Enforcer from locking the `pom.xml`.

**The Solution: Strategic Filesystem Pivot**

To resolve this, the development environment was strategically migrated from the Windows-mounted drive to the Native Linux Filesystem (`EXT4`).
- **Optimization:** By moving the project to the Linux Native Root (`~/gsoc/`), we bypassed the 9P bridge entirely.
- **Performance Gain:** Achieved a 10x improvement in I/O stability and reduced build times to ~15 seconds.

### Test-Driven Development (TDD) Workflow

We have moved to a strict Red-Green-Refactor pipeline to ensure the Agentic Architecture is bulletproof before deployment.
- **Phase 1 (Red):** Define JUnit assertions in `src/test/java` for the Orchestrator logic.
- **Phase 2 (Green):** Implement minimal Java logic to satisfy the Maven compiler and generate the `.hpi` artifact.
- **Phase 3 (Refactor):** Apply the Spotless Maven Plugin to ensure all code adheres to the official Jenkins Project community standards.

**Verification Command:**
```bash
# Clean, Format, and Build the verified HPI artifact
mvn spotless:apply clean install -DskipTests=false
```

This plugin was developed as part of a Google Summer of Code 2025 project.

## Prerequisites

- **Python**: 3.11+
- **Build tools**: `make`, `cmake` (≥3.14), C/C++ compiler (`gcc`/`clang`/MSVC)
- **Java**: JDK 11+ and Maven 3.6+ (for plugin development)

### Example system package installation

```bash
# Ubuntu/Debian/WSL
sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev

# macOS
brew install cmake python@3.11 && xcode-select --install
```



## Getting Started

There are two ways to run the API locally, depending on your use case:

### Option 1: Lite Mode (Recommended for Most Contributors)

Use this if you're working on the API, backend logic, data pipeline, or tests and don't need to test the actual chatbot responses.

```bash
make dev-lite
```

This will:
- Set up the Python environment automatically
- Install dependencies (skips the 4GB model download)
- Start the API server without loading the LLM

**Configuration**:
Before running the API, you can configure the Jenkins runtime data connection in `chatbot-core/api/config/config.yml` under the `jenkins` block:
```yaml
jenkins:
  url: "http://localhost:8080"
  user: "admin"
  token: "your-api-token"
  simulate_runtime_data: true # Set to false to connect to a real Jenkins instance
```

The API will be available at `http://127.0.0.1:8000` within a few minutes.

Verify it's working:
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
```

**What works:** All API endpoints, session management, context search, data pipeline  
**What doesn't work:** Actual chat completions (no model loaded)

### Option 2: Full Mode (For Testing Chat Functionality)

Use this if you need to test the chatbot with real LLM responses or work on model-specific features.

First, complete the full setup in [docs/setup.md](docs/setup.md). This includes installing llama-cpp-python and downloading the 4GB model.

Then run:
```bash
make api
```

The API will be available at `http://127.0.0.1:8000`.

**What works:** Everything, including actual chat completions with the local LLM

---

See [docs/README.md](docs/README.md) for detailed explanations.

## 🎥 Setup Video Tutorial

[![Local Setup Video Tutorial](https://img.youtube.com/vi/1DnMNA4aLyE/0.jpg)](https://youtu.be/1DnMNA4aLyE)

The tutorial shows how to fork the repo, set up the backend, download the LLM model, run the frontend, and verify the chatbot works.



## Troubleshooting

### WSL2 Filesystem Issues (`Unknown packaging: hpi` or `p9io.cpp` Errors)

- **Cause**: Working on a Windows-mounted drive (`/mnt/`) in WSL2. High-frequency metadata requests trigger deadlocks in the 9P bridge.
- **Fix**: Move your project directory to the Linux native home directory:
  ```bash
  mv /mnt/c/users/name/project ~/project
  ```

### Maven Enforcer Failures

- **Symptom**: Build fails with "Banned Dependencies" or "RequireUpperBoundDeps".
- **Fix**: Ensure you are using **JDK 17** and running the build in the native filesystem to allow proper dependency locking.

### Model Downloads
- **Symptom**: The application appears "stuck" or frozen during the first run of the data pipeline or API.
- **Cause**: The system is downloading the embedding model (`all-MiniLM-L6-v2`, ~80MB) or initializing the LLM.
- **Solution**: This is normal behavior for the first run. Please wait for a few minutes. Ensure you have a stable internet connection.

### Python Version Mismatches
- **Symptom**: `SyntaxError` or `ModuleNotFoundError` during setup or execution.
- **Solution**: 
  - Ensure you are using **Python 3.11+**. Verify with `python --version`.
  - Ensure the virtual environment is activated:
    ```bash
    source chatbot-core/venv/bin/activate
    ```

### Common Startup Errors
- **Memory Limits**: If the process is killed (e.g., `OOM Killed`), ensure your machine has sufficient RAM (at least 8GB recommended for full mode). Try running in **Lite Mode** (`make dev-lite`) first.
- **Missing Dependencies**: If you see import errors, re-run dependency installation:
  ```bash
  pip install -r chatbot-core/requirements.txt
  ```
- **llama-cpp-python installation fails**: Ensure build tools (gcc, cmake) are installed. See [docs/setup.md](docs/setup.md) for platform-specific instructions.

### Verification Steps
To confirm your local setup is correct:
1. **Virtual Environment**: Ensure `(venv)` appears in your terminal prompt.
2. **Lite Mode Check**: Run `make dev-lite`. It should start without errors.
3. **API Check**: Run `curl -X POST http://127.0.0.1:8000/api/chatbot/sessions`. It should return a default session response.

For more details, see [docs/setup.md](docs/setup.md).

## Developer Documentation

Development-related documentation can be found in the [`docs/`](docs/) directory.

- [Setup Guide](docs/setup.md)
- [Windows/WSL2 Setup Guide](docs/windows-setup.md) — for contributors on Windows machines

## Contributing

Refer to our [contribution guidelines](https://github.com/jenkinsci/.github/blob/master/CONTRIBUTING.md)

## LICENSE

Licensed under MIT, see [LICENSE](LICENSE.md)


