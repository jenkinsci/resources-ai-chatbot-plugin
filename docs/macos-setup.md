# macOS / Apple Silicon Setup Guide

This guide provides step-by-step instructions for setting up the
Jenkins AI Chatbot plugin locally on macOS with Apple Silicon (M1/M2/M3).

## Prerequisites

- macOS with Apple Silicon (M1, M2, or M3)
- Python 3.11+
- Node.js 18+
- Java JDK 11+ and Maven 3.6+
- Homebrew

## Installation Steps

### 1. Install System Dependencies

```bash
brew install cmake
xcode-select --install
```

### 2. Clone the Repository

```bash
git clone https://github.com/jenkinsci/resources-ai-chatbot-plugin
cd resources-ai-chatbot-plugin
```

### 3. Setup the Backend

```bash
cd chatbot-core
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-cpu.txt
pip install python-multipart
pip install llama-cpp-python
```

> **Note:** `llama-cpp-python` and `python-multipart` are required
> but not listed in `requirements-cpu.txt`. They must be installed
> manually before running the API.

### 4. Download the LLM Model (~4GB)

```bash
mkdir -p api/models/mistral
curl -L -o api/models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

### 5. Enable Apple Metal GPU Acceleration

Open `chatbot-core/api/config/config.yml` and change:

```yaml
# Change this
gpu_layers: 0

# To this
gpu_layers: 32
```

> **Important:** The default `gpu_layers: 0` causes all inference
> to run on CPU, resulting in response times of 5+ minutes. Setting
> it to 32 enables Apple Metal GPU acceleration, reducing response
> time to under 30 seconds.

### 6. Run the Data Pipeline

From the repo root:

```bash
cd ..
make run-data-pipeline
```

Monitor progress:

```bash
tail -f logs/data-pipeline.log
```

> **Note:** This may take a while. This only needs to be run once. Embeddings are persisted
> to disk.

### 7. Start the Backend

From the repo root:

```bash
IS_CPU_REQ=1 make api
```

> **Note:** The `IS_CPU_REQ=1` flag ensures `requirements-cpu.txt`
> is used instead of `requirements.txt`, avoiding numpy version
> conflicts.

API available at `http://127.0.0.1:8000`

### 8. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

> **Note:** Run this in a new terminal tab

Frontend available at `http://localhost:5173`

## Verifying Your Setup

Once both frontend and backend are running, open
`http://localhost:5173` in your browser and send a test message.
You should see a response within 30 seconds with GPU acceleration enabled.

You can also verify the API directly:

```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions \
  -H "Content-Type: application/json"
```

## Common Issues

### LLM not loading

- Ensure `llama-cpp-python` is installed in the venv
- Verify the model file exists at
  `chatbot-core/api/models/mistral/mistral-7b-instruct-v0.2.Q4_K_M.gguf`
- Check that `gpu_layers: 32` is set in `config.yml`

### Slow responses (5+ minutes)

- This indicates CPU-only inference
- Ensure `gpu_layers: 32` is set in `config.yml`
- Verify Metal GPU support: `system_profiler SPDisplaysDataType | grep Metal`

### numpy version conflict

- Use `IS_CPU_REQ=1 make api` instead of `make api`
- This uses `requirements-cpu.txt` which avoids the numpy
  version conflict present in `requirements.txt`

### Backend already set up message

- If you see "Backend already set up. Skipping...", the venv
  already exists
- To reinstall dependencies: `make clean` then `IS_CPU_REQ=1 make api`
