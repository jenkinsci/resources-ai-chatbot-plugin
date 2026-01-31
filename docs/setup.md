# Setup Instructions

This guide provides installation instructions for Linux and Windows, along with automated setup using the Makefile.

## Choose Your Setup Method

### Quick Start (Lite Mode)

**For:** Most contributors working on API, backend, or data pipeline features

```bash
make dev-lite
```

This will:
- Set up the Python virtual environment
- Install dependencies (skips the 4GB model and GPU packages)
- Start the API server without loading the LLM

The API runs at `http://127.0.0.1:8000` within a few minutes.

**Works:** All API endpoints, session management, context search, data pipeline  
**Doesn't work:** Chat completions (no model loaded)

**Use this when:**
- Working on API endpoints or backend services
- Developing data pipeline features
- Running tests
- You don't need to test actual chatbot responses

### Full Installation (With LLM)

**For:** Testing complete chat functionality or working on model-specific features

Follow the platform-specific installation guide below to:
- Install llama-cpp-python with GPU support
- Download the 4GB Mistral model
- Set up the complete environment

Then run:
```bash
make api
```

**Works:** Everything, including real chat completions with the local LLM

**Use this when:**
- Testing the complete chatbot experience
- Working on prompt engineering or model integration
- Debugging inference issues
- Preparing for production deployment

---

## Full Installation Guide

## Installation Guide for Linux

### Prerequisites
* Python 3.11 or later
* Git (to clone the repository)
* Maven (for the Java components)
* Sufficient disk space (at least 5GB for models and dependencies)

### Installation Steps

1. **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd resources-ai-chatbot-plugin
    ```

2. **Build the Maven Project**
    ```bash
    mvn install
    ```
3. **Set Up the Python Environment**

    Navigate to the Python subproject directory:
    
    ```bash
    cd chatbot-core
    ```

    Create a Python virtual environment:
    ```bash
    python3 -m venv venv
    ```
    
    Activate the virtual environment
    ```bash
    source venv/bin/activate
    ```
4. **Install the dependencies**
    ```bash
    pip install -r requirements.txt
    ```

    > **Note:** The backend requires `python-multipart` for multipart form handling.
    > This dependency is included in the requirements file, but if you encounter
    > runtime errors related to multipart requests, ensure it is installed:
    >
    > ```bash
    > pip install python-multipart
    > ```

5. **Set the `PYTHONPATH` to the current directory(`chatbot-core/`)**
    ```bash
    export PYTHONPATH=$(pwd)
    ```
6. **Download the Required Model**
    1. Create the model directory if it doesn't exist:
        ```bash
        mkdir -p api\models\mistral
        ```
    2. Download the Mistral 7B Instruct model from Hugging Face:
        * Go to https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
        * Download the file named `mistral-7b-instruct-v0.2.Q4_K_M.gguf`
        * Place the downloaded file in `api\models\mistral\`

By default, the backend attempts to load the local GGUF model during
startup. If the model file is missing, the server will fail to start.

Contributors who do not need local inference can run the backend
without a model by using test mode
(see “Running without a local LLM model (test mode)” below).


## Installation Guide for Windows
This guide provides step-by-step instructions for installing and running the Jenkins Chatbot on Windows systems.

### Prerequisites
* Windows 10 or 11
* Python 3.11 or later
* Git (to clone the repository)
* Maven (for the Java components)
* Sufficient disk space (at least 5GB for models and dependencies)

### Installation Steps

1. **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd resources-ai-chatbot-plugin
    ```

2. **Build the Maven Project**
    ```bash
    mvn install
    ```
3. **Set Up the Python Environment**

    Navigate to the Python subproject directory:
    
    ```bash
    cd chatbot-core
    ```

    Create a Python virtual environment:
    ```bash
    python3 -m venv venv
    ```
    
    Activate the virtual environment
    ```bash
    .\venv\Scripts\activate
    ```

4. **Install Dependencies**

    Install the Python dependencies using the CPU-only requirements file to avoid NVIDIA CUDA dependency issues:
    ```bash
    pip install -r requirements-cpu.txt
    ```
    > **Note:** The backend requires `python-multipart` for multipart form handling.
    > This dependency is included in the requirements file, but if you encounter
    > runtime errors related to multipart requests, ensure it is installed:
    >
    > ```powershell
    > pip install python-multipart
    > ```

    > **Note**: If you encounter any dependency issues, especially with NVIDIA packages, use the `requirements-cpu.txt` file which excludes GPU-specific dependencies.

5. **Set the PYTHONPATH**

    Set the PYTHONPATH environment variable to the current directory:

    ```bash
    $env:PYTHONPATH = (Get-Location).Path
    ```

6. **Download the Required Model**
    1. Create the model directory if it doesn't exist:
        ```bash
        mkdir -p api\models\mistral
        ```
    2. Download the Mistral 7B Instruct model from Hugging Face:
        * Go to https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
        * Download the file named `mistral-7b-instruct-v0.2.Q4_K_M.gguf`
        * Place the downloaded file in `api\models\mistral\`

By default, the backend attempts to load the local GGUF model during
startup. If the model file is missing, the server will fail to start.

Contributors who do not need local inference can run the backend
without a model by using test mode
(see “Running without a local LLM model (test mode)” below).

## Automatic setup

To avoid running all the steps each time, we have provided a target in the `Makefile` to automate the setup process.

To run it:
```bash
make setup-backend
```

By default the target will use the `requirements.txt` to install the dependencies. In case you would like to run it with the cpu requirements run:
```bash
make setup-backend IS_CPU_REQ=1
```

> **Note:** The same logic holds for every other target that will be presented.

> **Note:** The target **does not** include the installation of the LLM.

### What does `setup-backend` do?

The `setup-backend` Makefile target prepares the Python backend by:
- Creating a virtual environment in `chatbot-core/venv`
- Installing backend dependencies from `requirements.txt`
  (or `requirements-cpu.txt` when `IS_CPU_REQ=1` is set)

You usually do not need to run this manually.
The `make api` target automatically runs `setup-backend`
if the backend has not already been set up.

## Running without a local LLM model (test mode)

By default, the backend loads a local GGUF model on startup.
For contributors who do not need local inference, a test configuration
is available.

The backend includes a `config-testing.yml` file that disables local
LLM loading. This configuration is activated when the
`PYTEST_VERSION` environment variable is set.

Example:

```bash
PYTEST_VERSION=1 make api
```

## Common Troubleshooting

This section covers common issues encountered during setup, especially when installing
dependencies that require native compilation (e.g. `llama-cpp-python`).

---

### llama-cpp-python fails to install

**Symptoms**
- `pip install llama-cpp-python` fails
- Errors mentioning `cmake`, `gcc`, or “failed building wheel”

**Cause**
`llama-cpp-python` requires a working C/C++ toolchain and CMake to build native extensions.

**Solution**
For Linux (Ubuntu/Debian):
```bash
sudo apt install build-essential cmake
pip install llama-cpp-python

For macOS:
```bash
brew install cmake
pip install llama-cpp-python    
```