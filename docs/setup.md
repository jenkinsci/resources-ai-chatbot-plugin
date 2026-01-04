# Setup Instructions

For the setup instructions have been provided for *Linux* and *Windows*. Moreover in the last section the automated setup using targets from the `Makefile` are discussed.

## Installation Guide for Linux

### Prerequisites
* Python 3.11, 3.12, or 3.13
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

## Installation Guide for Windows
This guide provides step-by-step instructions for installing and running the Jenkins Chatbot on Windows systems.

### Prerequisites
* Windows 10 or 11
* Python 3.11, 3.12, or 3.13
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
```

For macOS:
```bash
brew install cmake
pip install llama-cpp-python    
```