# Resources AI Chatbot Plugin — End-User Guide

> **Related Issues:** [#388](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/388) · [#278](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/278)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
   - [4.1 API URL Setup](#41-api-url-setup)
   - [4.2 Jenkins System Configuration](#42-jenkins-system-configuration)
5. [Running the Backend API](#5-running-the-backend-api)
   - [5.1 Lite Mode (Recommended)](#51-lite-mode-recommended)
   - [5.2 Full Mode (Real LLM Responses)](#52-full-mode-real-llm-responses)
6. [Using the Chatbot](#6-using-the-chatbot)
7. [Example Queries](#7-example-queries)
8. [Troubleshooting](#8-troubleshooting)
9. [FAQ](#9-faq)

---

## 1. Overview

The **Resources AI Chatbot Plugin** embeds an AI-powered assistant directly into the Jenkins interface. It lets you ask questions in plain English and get instant answers about Jenkins documentation, plugins, and community resources — without leaving Jenkins.

**Who this guide is for:** Jenkins administrators and end-users who want to install, configure, and start using the chatbot. If you are a developer looking to contribute code, see [`docs/setup.md`](./setup.md) instead.

**Key capabilities:**

- Ask natural-language questions about Jenkins (e.g. _"How do I create a Multibranch Pipeline?"_)
- Get direct answers from official Jenkins documentation
- Look up plugin information and community resources
- Upload files to provide additional context to the chatbot

---

## 2. Prerequisites

Before installing the plugin, make sure your system meets the following requirements.

### Jenkins

| Requirement | Minimum Version |
|---|---|
| Jenkins | 2.387.3 LTS or later |
| Java | JDK 11 or later |

### Backend API (required to use the chatbot)

The chatbot needs a running Python-based API server. You need:

| Requirement | Details |
|---|---|
| Python | 3.11 or later |
| Build tools | `make`, `cmake` ≥ 3.14, a C/C++ compiler (`gcc`/`clang`) |
| RAM | At least 4 GB (8 GB recommended for Full Mode) |
| Disk space | ~500 MB for Lite Mode; ~5 GB for Full Mode (includes a 4 GB LLM model) |
| Internet | Required on first run to download models |

**Install system packages:**

```bash
# Ubuntu / Debian / WSL
sudo apt install -y make cmake gcc g++ python3.11 python3.11-venv python3.11-dev

# macOS
brew install cmake python@3.11 && xcode-select --install
```

---

## 3. Installation

### Step 1 — Install the plugin from the Jenkins Update Center

1. Open Jenkins and go to **Manage Jenkins → Plugins → Available plugins**.
2. Search for **Resources AI Chatbot**.
3. Check the box next to it and click **Install**.
4. Restart Jenkins when prompted.

### Step 2 — Verify the plugin is active

After restart, go to **Manage Jenkins → Plugins → Installed plugins** and confirm **Resources AI Chatbot** appears in the list with status **Enabled**.

---

## 4. Configuration

### 4.1 API URL Setup

The Jenkins plugin communicates with a backend API server. You must tell Jenkins where that server is running.

1. Go to **Manage Jenkins → System**.
2. Scroll down to the **Resources AI Chatbot** section.
3. In the **API URL** field, enter the address of your running backend server.
   - Default local address: `http://127.0.0.1:8000`
   - Remote server example: `http://your-server-host:8000`
4. Click **Save**.

> **Tip:** If the API URL field is not visible in Jenkins System Configuration, ensure the plugin is installed and Jenkins has been fully restarted. This was a known issue reported in [#278](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/278).

### 4.2 Jenkins System Configuration

| Field | Description | Default |
|---|---|---|
| API URL | The address of your chatbot backend API | `http://127.0.0.1:8000` |

After saving, the chatbot icon will appear in the Jenkins sidebar and top navigation bar.

---

## 5. Running the Backend API

The chatbot's AI logic runs as a separate Python API server. You must start this server before the plugin can respond to any queries.

Clone the repository (first time only):

```bash
git clone https://github.com/jenkinsci/resources-ai-chatbot-plugin.git
cd resources-ai-chatbot-plugin
```

### 5.1 Lite Mode (Recommended)

Use this mode if you just want to try the chatbot or if your machine has limited resources. It skips the 4 GB model download and uses a simpler response mechanism.

```bash
make dev-lite
```

The API will be available at `http://127.0.0.1:8000` within a few minutes.

**What works in Lite Mode:**
- All API endpoints
- Session management
- Context search (finds relevant docs)
- Data pipeline

**What does NOT work in Lite Mode:**
- Full AI-generated chat responses (no LLM loaded)

**Verify it is running:**

```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
```

You should see a JSON response with a session ID. If you do, the API is ready.

### 5.2 Full Mode (Real LLM Responses)

Use this mode if you want real AI-generated answers. This downloads a 4 GB language model on the first run.

1. Complete the full setup first (installs `llama-cpp-python` and downloads the model):
   ```bash
   # See docs/setup.md for the full step-by-step guide
   ```

2. Then start the API:
   ```bash
   make api
   ```

The API will be available at `http://127.0.0.1:8000`.

> **Note:** The first run may appear frozen for several minutes. This is normal — the system is downloading the embedding model (~80 MB) and/or initializing the LLM (~4 GB). Do not close the terminal. Ensure you have a stable internet connection.

---

## 6. Using the Chatbot

Once the plugin is installed, the backend is running, and the API URL is configured:

1. Open any Jenkins page.
2. Click the **chatbot icon** (💬) in the Jenkins top navigation or sidebar.
3. A chat panel will open on the right side of the screen.
4. Type your question in the input box and press **Enter** or click **Send**.
5. The chatbot will respond with relevant information from Jenkins documentation and resources.

**File upload:** You can also attach a file (e.g. a Jenkinsfile or a log output) using the attachment button in the chat panel. The chatbot will use the file content as additional context for your question.

---

## 7. Example Queries

Here are some questions you can ask the chatbot:

| What you want to know | Example question |
|---|---|
| How to create a pipeline | _"How do I create a Multibranch Pipeline?"_ |
| Plugin information | _"What does the Docker Pipeline plugin do?"_ |
| Jenkinsfile syntax | _"How do I use `when` conditions in a declarative pipeline?"_ |
| Build failure help | _"My build failed with 'No such file or directory'. What should I check?"_ |
| General concepts | _"What is the difference between Freestyle and Pipeline jobs?"_ |
| Community resources | _"Where can I find the Jenkins community forum?"_ |

---

## 8. Troubleshooting

### The chatbot icon does not appear in Jenkins

- Confirm the plugin is installed and enabled: **Manage Jenkins → Plugins → Installed plugins**.
- Restart Jenkins completely (not just a soft reload).
- Clear your browser cache and reload.

### The chatbot shows an error or does not respond

- Confirm the backend API is running. Open a terminal and run:
  ```bash
  curl -X POST http://127.0.0.1:8000/api/chatbot/sessions
  ```
  If this fails, the API server is not running. Start it with `make dev-lite` or `make api`.
- Confirm the API URL in Jenkins System Configuration matches where your API server is running.

### The API URL field is missing from Jenkins System Configuration

This was reported in [#278](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/278). Try:
1. Uninstall and reinstall the plugin.
2. Perform a full Jenkins restart (not a safe restart).
3. Clear your browser cache.
4. If the issue persists, [open a new issue](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/new) with your Jenkins version and plugin version.

### The API server appears frozen / stuck on first run

- **Cause:** The system is downloading the embedding model (`all-MiniLM-L6-v2`, ~80 MB) or the LLM (~4 GB).
- **Solution:** Wait several minutes. Do not interrupt the process. Check your internet connection.

### `SyntaxError` or `ModuleNotFoundError` when starting the API

- Confirm you are using Python 3.11 or later:
  ```bash
  python --version
  ```
- Confirm the virtual environment is activated:
  ```bash
  source chatbot-core/venv/bin/activate
  ```
- Reinstall dependencies:
  ```bash
  pip install -r chatbot-core/requirements.txt
  ```

### `OOM Killed` / Out of Memory error

- Your machine does not have enough RAM for Full Mode.
- Switch to Lite Mode:
  ```bash
  make dev-lite
  ```
- Ensure at least 4 GB RAM is free before starting the API.

### `llama-cpp-python` installation fails

- Ensure `gcc` and `cmake` are installed (see [Prerequisites](#2-prerequisites)).
- See [`docs/setup.md`](./setup.md) for platform-specific build instructions.

---

## 9. FAQ

**Q: Do I need to configure anything in Jenkins besides the API URL?**  
A: No. Once the API URL is saved and the backend is running, the chatbot is ready to use.

**Q: Does the chatbot send my data to an external server?**  
A: No. By default, the LLM runs entirely on your local machine. No data is sent to any external AI service. The only network activity is downloading the model files on the first run.

**Q: Can I host the backend API on a separate machine?**  
A: Yes. Start the API on any machine accessible by your Jenkins server, then set the API URL in Jenkins System Configuration to that machine's address and port (e.g. `http://192.168.1.50:8000`).

**Q: What Jenkins versions are supported?**  
A: Jenkins 2.387.3 LTS and later. JDK 11 or later is required.

**Q: The chatbot answers seem incomplete or incorrect. What can I do?**  
A: Try Full Mode (`make api`) for better answer quality. In Lite Mode, actual AI-generated responses are disabled. If answers are still incorrect in Full Mode, [open an issue](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/new) with an example query and the response you received.

**Q: Where can I get more help?**  
A: Visit the [Jenkins community forum](https://community.jenkins.io) or open an issue on [GitHub](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues).

---

*This document addresses the end-user documentation gap described in [#388](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/388) and [#278](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/278).*