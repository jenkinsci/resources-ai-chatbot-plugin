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

```bash
make api
```

API will be available at `http://127.0.0.1:8000`

**Verify it's working:**

```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
```

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

## Troubleshooting

**llama-cpp-python installation fails:**

```bash
sudo apt install build-essential cmake  # Linux
brew install cmake  # macOS
pip install llama-cpp-python
```

**API crashes on startup:**

```bash
cd chatbot-core && source venv/bin/activate
pip install llama-cpp-python retriv
```

**Clean and rebuild:**

```bash
make clean && make setup-backend IS_CPU_REQ=1
```

## Documentation

- Setup details: [docs/setup.md](docs/setup.md)
- Architecture: [docs/README.md](docs/README.md)
- API docs: [docs/chatbot-core/api/](docs/chatbot-core/api/)

## License

MIT License - see [LICENSE.md](LICENSE.md)
