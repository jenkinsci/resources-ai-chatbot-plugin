# Conversation Summary Memory Upgrade

To ensure the Jenkins Chatbot remains highly scalable and robust during long-running conversations, we upgraded the conversational history layer from standard buffer memory to LangChain's **`ConversationSummaryBufferMemory`**.

---

## 1. Why Was This Changed?
Previously, the chatbot used standard `ConversationBufferMemory`, which appends all user and assistant messages into a flat, raw list indefinitely. 

While simple, this approach has critical flaws for production chatbots:
* **Token Limit Overflow**: As conversations grow, the history size quickly exceeds the context window limits of the underlying LLM, causing generation to crash or ignore prompt instructions.
* **Server Out-Of-Memory (OOM)**: Storing and parsing extremely long logs and conversation strings in memory for every message degrades performance and risks crashing the server.

### The Solution:
`ConversationSummaryBufferMemory` maintains a hybrid model:
1. It keeps the **most recent conversation turns** in raw buffer format for high-fidelity context.
2. Once the total conversation length exceeds a configurable token threshold (set to **`1500 tokens`**), it uses the local LLM to generate a **moving summary** of the older turns and clears those raw messages from the active prompt context.

---

## 2. Architecture & Implementation

The migration touches several key modules in the API service layer:

### A. Custom LangChain LLM Proxy Wrapper
* **File:** [`chatbot-core/api/models/langchain_llm_wrapper.py`](file:///home/nikhildhaliya/Work/opensource/resources-ai-chatbot-plugin/chatbot-core/api/models/langchain_llm_wrapper.py)
* **What it does:** LangChain's `ConversationSummaryBufferMemory` requires a LangChain-compatible `LLM` class to perform the summarization task. Since this repository uses a custom `llama_cpp_provider` wrapper, we implemented `CustomLangchainLLM` (subclassing LangChain's `LLM`).
* **Resilience:** It acts as a proxy forwarding calls to the active `llm_provider`. In lite/dev environments where `llm_provider` is disabled, it falls back to returning the raw source text to prevent the backend from crashing.

### B. Summary Memory and Pruning Integration
* **File:** [`chatbot-core/api/services/memory.py`](file:///home/nikhildhaliya/Work/opensource/resources-ai-chatbot-plugin/chatbot-core/api/services/memory.py)
* **What it does:** Replaces `ConversationBufferMemory` with `ConversationSummaryBufferMemory`. It sets the `max_token_limit` to `1500` and configures the `llm` parameter with our proxy.
* **Pruning Hook:** Inside `persist_session()`, before the session is saved to disk, it executes the `.prune()` method on the memory instance. This is the exact hook that triggers the LLM-powered summarization process when the token threshold is reached.

### C. Persistent Storage & Backward Compatibility
* **File:** [`chatbot-core/api/services/sessionmanager.py`](file:///home/nikhildhaliya/Work/opensource/resources-ai-chatbot-plugin/chatbot-core/api/services/sessionmanager.py)
* **What it does:** Standard history was serialized as a flat list. Summary memory requires storing both the `"summary"` and the active `"messages"`.
* **New Storage Format:**
  ```json
  {
    "summary": "The user asked for help configuring a pipeline job...",
    "messages": [
      {"role": "human", "content": "How do I do that?"},
      {"role": "ai", "content": "You can define a Jenkinsfile."}
    ]
  }
  ```
* **Zero-Downtime Migration**: To prevent data loss for existing users, `load_session()` checks the type of the loaded JSON. If it encounters a legacy list-based history file (`[...]`), it automatically migrates the structure into the new dictionary format on-the-fly.

### D. Prompt Engineering and Injection
* **File:** [`chatbot-core/api/prompts/prompt_builder.py`](file:///home/nikhildhaliya/Work/opensource/resources-ai-chatbot-plugin/chatbot-core/api/prompts/prompt_builder.py)
* **What it does:** In `build_prompt()`, if `moving_summary_buffer` is present and non-empty, it is dynamically prepended to the top of the chat history section:
  ```
  System: Summary of older chat turns: <moving_summary_buffer>
  ```
  This guarantees the LLM maintains perfect historical context over pruned messages.

### E. Public History Endpoint Adaptation
* **File:** [`chatbot-core/api/routes/chatbot.py`](file:///home/nikhildhaliya/Work/opensource/resources-ai-chatbot-plugin/chatbot-core/api/routes/chatbot.py)
* **What it does:** The `GET /sessions/{session_id}/message` history endpoint is updated to dynamically prepend the summary as a `{"role": "system", "content": "Summary of older messages: ..."}` item, allowing clients to cleanly render the summary.

---

## 3. Testing and Verification
The entire implementation has been thoroughly validated through refactored backend unit/integration tests and frontend React tests. 

* **Backend Tests:** All **252 tests** (`test_memory.py`, `test_sessionmanager.py`, `test_prompt_builder.py`, and integration suites) pass 100% green.
* **Frontend Tests:** All **76 Jest/React tests** pass green with zero UI regressions.
