# API

This section documents the API component of the chatbot. It exposes the functionality as a RESTful service using FastAPI.

## Starting the server

Before launching the FastAPI server, you must first install the required GGUF model:

1. Download the **Mistral 7B Instruct (v0.2 Q4_K_M)** model from Hugging Face:
   [https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)

2. Place the downloaded `.gguf` file in:
   ```
   api/models/mistral/
   ```

Once the model is in place:

3. Navigate to the project root:
   ```bash
   cd chatbot-core
   ```

4. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

5. Start the server with Uvicorn:
   ```bash
   uvicorn api.main:app --reload
   ```

By default, the API will be available at `http://127.0.0.1:8000`.

> **Note**: Adding `--host 0.0.0.0` makes the server accessible from other devices on the network. If you only need local access, you can omit this parameter.

## Available Endpoints

Here’s a summary of the API routes and their expected request/response structures:

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

## Architecture Overview

The API is organized with a clean separation of concerns:

- **Controller layer** (`api/routes/`): Defines FastAPI routes. Responsible for request validation, status code handling, and delegating logic to services.
- **Service layer** (`api/services/`): Implements the core logic of chat handling, including memory management, retrieval, and LLM generation.
- **Model/schema definitions** (`api/models/`): Contains Pydantic classes for request/response models and the LLM abstraction interface.
- **Prompt builder** (`api/prompts/`): Contains utilities to structure LLM prompts in a consistent format.
- **Configuration** (`api/config/`): Handles loading configuration from `config.yml`.

## Session Memory Management

Chat memory is managed **in-memory** using LangChain's `ConversationBufferMemory`, stored in a module-level dictionary keyed by `session_id`.

This allows the assistant to maintain conversation history across multiple chats.

Future improvements may include:
- Persisting memory to Redis
- Supporting timeout or expiration per session

## LLM Abstraction and Extensibility

The API uses an abstract base class (`LLMProvider`) to decouple the chatbot logic from the underlying language model.

Currently, it is implemented by `llama_cpp_provider` that runs a local GGUF model (Mistral 7B Instruct).

**Future provider options could include:**
- OpenAI's `gpt-3.5` or `gpt-4` via API
- Google's Gemini via API
- Any model served over an external endpoint

This is useful to give users with computing resources constraints the possibility to eventually use their API keys.
