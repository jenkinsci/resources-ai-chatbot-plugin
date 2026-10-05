# API

This section documents the API component of the chatbot. It exposes the functionality as a RESTful service using FastAPI.

## Starting the server

Start the FastAPI service from the repository root with the Makefile targets. The targets create the Python environment and install dependencies when they are not already available.

For API, backend, or data-pipeline development, use lite mode:

```bash
make dev-lite
```

Lite mode starts the service without loading a local LLM. Use full mode when you need local model responses:

```bash
make api
```

Full mode requires the GGUF model described in the [setup guide](../../setup/README.md).
The API is available at `http://127.0.0.1:8000` by default.

If you do not want to download the local model, configure a hosted provider and its API key for LiteLLM, then start the backend in lite mode. The selected provider is used for chat requests through the same API, so local model inference is not required for hosted-provider usage. Provider configuration is documented in the [third-party provider integration guide](../litellm.md).

For local plugin development, keep the backend running in one terminal and start Jenkins with the bundled frontend in another:

```text
Terminal 1: make api
Terminal 2: mvn hpi:run
```

The plugin installation and backend URL configuration are documented in the [plugin installation guide](../../plugin-installation.md).

## Available Endpoints

Here’s a summary of the API routes and their expected request/response structures:

The following table summarizes all API routes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chatbot/sessions` | POST | Create a new chat session |
| `/api/chatbot/sessions/{session_id}/message` | POST | Send a message to the chatbot |
| `/api/chatbot/sessions/{session_id}/message` | GET | Retrieve conversation history |
| `/api/chatbot/sessions/{session_id}/message/upload` | POST | Send a message with file attachments |
| `/api/chatbot/sessions/{session_id}` | DELETE | Delete a session |
| `/api/chatbot/sessions/{session_id}/stream` | WebSocket | Real-time token streaming |
| `/api/chatbot/files/supported-extensions` | GET | List supported upload file types |
| `/health` | GET | Service health check |

### `POST /api/chatbot/sessions`

Creates a new chat session.

**Response:**
```json
{
  "session_id": "string"
}
```

### `POST /api/chatbot/sessions/{session_id}/message`

Sends a user message to the chatbot and receives a generated response.

**Request body:**
```json
{
  "message": "string"
}
```

**Response:**
```json
{
  "reply": "string"
}
```

---

### `DELETE /api/chatbot/sessions/{session_id}`

Deletes an existing session.

**Response:**
```json
{
  "message": "Session {session_id} deleted."
}
```

---

### `GET /api/chatbot/sessions/{session_id}/message`

Retrieves the conversation history for a session. Restores persisted sessions from disk if they are not currently in memory.

**Response:**
```json
{
  "session_id": "string",
  "messages": [
    {
      "role": "human",
      "content": "string"
    },
    {
      "role": "ai",
      "content": "string"
    }
  ]
}
```

**Error responses:**
- `404 Not Found`: Session does not exist.

---

### `POST /api/chatbot/sessions/{session_id}/message/upload`

Sends a user message with optional file attachments to the chatbot. Files are processed and their content is included in the context for the LLM.

**Request:**
- Content-Type: `multipart/form-data`
- `message` (form field, required): The user message.
- `files` (file field, optional): One or more uploaded files.

Supported file types include text files (`.txt`, `.log`, `.md`, `.json`, `.xml`, `.yaml`, `.yml`, code files) and image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`). Use the `/files/supported-extensions` endpoint for the full list.

**Response:**
```json
{
  "reply": "string"
}
```

**Error responses:**
- `404 Not Found`: Session does not exist.
- `400 Bad Request`: Unsupported file type, file too large, or content type mismatch.
- `422 Unprocessable Entity`: Both message is empty and no files provided.

---

### `WebSocket /api/chatbot/sessions/{session_id}/stream`

WebSocket endpoint for real-time token streaming. Streams chatbot responses token-by-token for a more interactive user experience.

**Connection:** Upgrade to WebSocket at the endpoint URL.

**Send (JSON):**
```json
{
  "message": "string"
}
```

**Receive (JSON, streamed token-by-token):**
```json
{"token": "partial response text"}
```

When the response is complete:
```json
{"end": true}
```

**Error responses (JSON over WebSocket):**
- `{"error": "Session not found"}`: Invalid session ID (connection closed after sending).
- `{"error": "Invalid JSON format."}`: Malformed input message.
- `{"error": "An unexpected error occurred."}`: Unexpected server error during streaming.

---

### `GET /api/chatbot/files/supported-extensions`

Returns the list of supported file extensions for upload, along with size limits.

**Response:**
```json
{
  "text": [".bash", ".cfg", ".conf", ".cpp", ".css", ".csv", ".env", ".go", ".groovy", ".html", ".java", ".js", ".json", ".log", ".md", ".php", ".properties", ".py", ".rb", ".rs", ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt", ".xml", ".yaml", ".yml"],
  "image": [".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"],
  "max_text_size_mb": 1.0,
  "max_image_size_mb": 5.0
}
```

> **Note:** The exact list of extensions and size limits are defined in `api/services/file_service.py` and may change as new file types are added.

---

### `GET /health`

Health check endpoint for container orchestration (Kubernetes, Docker, etc.).

> **Note:** This endpoint is registered on the root application, not under the `/api/chatbot` prefix.

**Response:**
```json
{
  "status": "healthy",
  "llm_available": true
}
```

The `llm_available` field indicates whether the local LLM model is loaded and ready to generate responses. It is `false` in lite mode, including when lite mode is being used with a hosted provider. Hosted-provider availability depends on the selected provider configuration and API key.

## Architecture Overview

The API is organized with a clean separation of concerns:

- **Controller layer** (`api/routes/`): Defines FastAPI routes. Responsible for request validation, status code handling, and delegating logic to services.
- **Service layer** (`api/services/`): Implements the core logic of chat handling, including memory management, retrieval, and LLM generation.
- **Model/schema definitions** (`api/models/`): Contains Pydantic classes for request/response models and the LLM abstraction interface.
- **Prompt builder** (`api/prompts/`): Contains utilities to structure LLM prompts in a consistent format.
- **Configuration** (`api/config/`): Handles loading configuration from `config.yml`.

## Session Memory Management

Chat memory is managed **in-memory** using LangChain's `ConversationBufferMemory`, stored in a module-level dictionary keyed by `session_id`.

This allows the assistant to maintain conversation history across multiple chats. Sessions are also persisted to disk as JSON files, enabling recovery across server restarts. A background task periodically cleans up expired sessions based on the configured timeout.

## LLM Abstraction and Extensibility

The API uses an abstract base class (`LLMProvider`) to decouple the chatbot logic from the underlying language model.

The provider abstraction supports both the local `llama_cpp_provider`, which runs a GGUF model, and hosted providers routed through LiteLLM.

Hosted-provider API keys are supplied through the local environment configuration and are not returned by the provider API. See the [third-party provider integration guide](../litellm.md) for provider setup and model selection.
