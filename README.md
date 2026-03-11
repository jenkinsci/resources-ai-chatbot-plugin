# Resources AI Chatbot Plugin

## Introduction

Beginners often struggle to take their first steps with Jenkins’ documentation and available resources. To address this challenge, this plugin integrates an AI-powered assistant directly into the Jenkins interface. It offers quick, intuitive support to users of all experience levels through a simple conversational UI.

The plugin is designed to reduce the learning curve for newcomers while also improving accessibility and productivity for experienced users.

This plugin was developed as part of a Google Summer of Code 2025 project.

## Prerequisites

- **Python**: 3.11+
- **Node.js**: 20+ (for frontend)
- **Build tools**: `make`, `cmake` (≥3.14), C/C++ compiler
- **Java**: JDK 11+ and Maven 3.6+ (for Jenkins plugin)

**Install system dependencies:**

```bash
# Ubuntu/Debian/WSL
sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev

# macOS
brew install cmake python@3.11 && xcode-select --install
```

## Quick Start

### 1. Setup Backend

From project root:

```bash
# For CPU-only (recommended for most systems)
make setup-backend IS_CPU_REQ=1

# For GPU support
make setup-backend
```

### 2. Download LLM Model

Download the Mistral model and place it in the correct location:

```bash
mkdir -p chatbot-core/api/models/mistral
# Download mistral-7b-instruct-v0.2.Q4_K_M.gguf from:
# https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
# Place it in: chatbot-core/api/models/mistral/
```

### 3. Run API

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

The API will be available at `http://127.0.0.1:8000` within a few minutes.

**Verify it's working:**

```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
```

**What works:** All API endpoints, session management, context search, data pipeline  
**What doesn't work:** Actual chat completions (no model loaded)

#### Option 2: Full Mode (For Testing Chat Functionality)

Use this if you need to test the chatbot with real LLM responses or work on model-specific features.

First, complete the full setup in [docs/setup.md](docs/setup.md). This includes installing llama-cpp-python and downloading the 4GB model.

Then run:

```bash
make api
```

The API will be available at `http://127.0.0.1:8000`.

**What works:** Everything, including actual chat completions with the local LLM

### 4. Build Frontend

```bash
make build-frontend
```

### 5. Run with Docker (Alternative)

**Prerequisites:**

- Docker and Docker Compose installed

**Steps:**

1. **Download LLM Model** (if not already done):

   ```bash
   mkdir -p chatbot-core/api/models/mistral
   # Download mistral-7b-instruct-v0.2.Q4_K_M.gguf from:
   # https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
   # Place it in: chatbot-core/api/models/mistral/
   ```

2. **Build and run containers:**

   ```bash
   docker-compose up --build
   ```

3. **Access services:**
   - Backend API: `http://127.0.0.1:8000`
   - Frontend UI: `http://127.0.0.1:80`
   - API Docs: `http://127.0.0.1:8000/docs`

**Stop containers:**

```bash
docker-compose down
```

**For GPU support:**

```bash
docker-compose -f docker-compose.gpu.yml up --build
```

## Data Pipeline

To populate the knowledge base with Jenkins documentation:

```bash
make run-data-pipeline
```

This collects, preprocesses, chunks, and stores data in the vector database.

## Testing

```bash
# Run all tests
make run-test

# Frontend tests only
make run-frontend-tests

# Backend tests only
make run-backend-tests
```

## 🎥 Setup Video Tutorial

[![Local Setup Video Tutorial](https://img.youtube.com/vi/1DnMNA4aLyE/0.jpg)](https://youtu.be/1DnMNA4aLyE)

The tutorial shows how to fork the repo, set up the backend, download the LLM model, run the frontend, and verify the chatbot works.



## Troubleshooting

**llama-cpp-python installation fails:**

```bash
sudo apt install build-essential cmake  # Linux
brew install cmake  # macOS
pip install llama-cpp-python
```

**API crashes on startup:**
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

```bash
cd chatbot-core && source venv/bin/activate
pip install llama-cpp-python retriv
```

**Clean and rebuild:**
- [Setup Guide](docs/setup.md)
- [Windows/WSL2 Setup Guide](docs/windows-setup.md) — for contributors on Windows machines

## Contributing

```bash
make clean && make setup-backend IS_CPU_REQ=1
```

## Documentation

- Setup details: [docs/setup.md](docs/setup.md)
- Architecture: [docs/README.md](docs/README.md)
- API docs: [docs/chatbot-core/api/](docs/chatbot-core/api/)

## License

MIT License - see [LICENSE.md](LICENSE.md)
