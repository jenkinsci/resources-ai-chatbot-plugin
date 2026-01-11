# Resources AI Chatbot Plugin

## Introduction

Beginners often struggle to take their first steps with Jenkins’ documentation and available resources. To address this challenge, this plugin integrates an AI-powered assistant directly into the Jenkins interface. It offers quick, intuitive support to users of all experience levels through a simple conversational UI.

The plugin is designed to reduce the learning curve for newcomers while also improving accessibility and productivity for experienced users.

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

You can run the application in two ways:

### Option 1: Docker Deployment (Recommended for Production)

The easiest way to get started is using Docker. This method handles all dependencies automatically and provides a production-ready setup.

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Quick Start:**
```bash
# 1. Download the llama.cpp model
mkdir -p chatbot-core/api/models/mistral
cd chatbot-core/api/models/mistral
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
cd ../../../../

# 2. Build and start services
docker-compose up -d

# 3. Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Using Make commands:**
```bash
make -f Makefile.docker up      # Start all services
make -f Makefile.docker logs    # View logs
make -f Makefile.docker health  # Check health
make -f Makefile.docker down    # Stop services
```

📖 **Full Docker documentation:** [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Option 2: Local Development Setup

For development and testing, you can run the application locally.

**Prerequisites:**
- Python 3.11+
- Build tools: `make`, `cmake` (≥3.14), C/C++ compiler
- Java JDK 11+ and Maven 3.6+ (for plugin development)

```bash
# Ubuntu/Debian/WSL
sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev

# macOS
brew install cmake python@3.11 && xcode-select --install
```

### Setup

Complete the full setup process in [docs/setup.md](docs/setup.md) before running any commands. This includes creating a virtual environment, installing Python dependencies (including llama-cpp-python), and configuring the data pipeline.

### Running the API


Once setup is complete, from the **project root directory** run:
```bash
make api
```

The API will be available at `http://127.0.0.1:8000`.

Verify it's working:
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
```



See [docs/README.md](docs/README.md) for detailed explanations.

## Troubleshooting

**llama-cpp-python installation fails**: Ensure build tools are installed and use Python 3.11+

**API crashes on startup**:
This may be caused by missing optional dependencies (e.g. `retriv`).

Try installing missing packages:
```bash
pip install llama-cpp-python retriv 
```

**General issues**: Run `make clean && make <target>`, verify your virtual environment is activated, and ensure all dependencies from [docs/setup.md](docs/setup.md) are installed.

## Developer Documentation

Development-related documentation can be found in the [`docs/`](docs/) directory.

## Contributing

Refer to our [contribution guidelines](https://github.com/jenkinsci/.github/blob/master/CONTRIBUTING.md)

## LICENSE

Licensed under MIT, see [LICENSE](LICENSE.md)


