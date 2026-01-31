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


