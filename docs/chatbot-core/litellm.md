# LiteLLM Provider Integration

## 1. What It Is

### Overview

The chatbot keeps the existing local `llama.cpp` provider and uses the LiteLLM Python SDK for hosted providers. LiteLLM gives the backend one interface for normal completions and streamed completions without adding a provider-specific Python class for each hosted model.

Provider selection is explicit. An unknown provider, missing API key, or hosted-provider failure does not fall back to another model.

---

## 2. Provider Catalog and Keys

### Catalog

[`chatbot-core/api/config/providers.json`](../../chatbot-core/api/config/providers.json) is the single source of truth for the providers shown by the application.

```json
{
  "id": "groq",
  "label": "Groq API",
  "model": "groq/model-name"
}
```

| Field | Purpose |
| --- | --- |
| `id` | Stable identifier sent with a chat request. |
| `label` | Name displayed in the model selector. |
| `model` | LiteLLM model identifier. |

[`providers.py`](../../chatbot-core/api/config/providers.py) validates the file. It requires at least one provider, normalizes IDs to lowercase, rejects blank or unknown fields, and rejects duplicate IDs.

### API Keys

A hosted provider's key name is derived from its ID:

```text
groq       -> GROQ_API_KEY
openrouter -> OPENROUTER_API_KEY
deepseek   -> DEEPSEEK_API_KEY
```

The catalog does not store keys. For local development, keys live in the ignored `chatbot-core/.env` file.

Run the synchronizer after editing the catalog:

```bash
make sync-provider-env
```

`ProviderManager` synchronizes the managed key block and reads `.env` during backend initialization. Restart the backend after changing the catalog or key values.

---

## 3. How It Runs

### Provider Metadata

The frontend loads the selector from:

```text
GET /api/chatbot/providers
```

Each response item contains `id`, `label`, `model`, and `configured`. `configured` is true for the local provider or when the matching API-key environment variable is non-empty. API-key values are never returned.

### Request Routing

The selected provider is sent with a normal JSON request, multipart upload, or WebSocket message. If omitted, the API defaults to `local`.

`ProviderManager` validates and activates the selected provider for the request. The existing retrieval and prompt pipeline is shared by both paths.

---

## 4. Code Structure

| File | Responsibility |
| --- | --- |
| [`providers.json`](../../chatbot-core/api/config/providers.json) | Defines visible local and hosted providers. |
| [`providers.py`](../../chatbot-core/api/config/providers.py) | Loads and validates the catalog. |
| [`env_sync.py`](../../chatbot-core/api/config/env_sync.py) | Maintains the managed `.env` key block. |
| [`provider_manager.py`](../../chatbot-core/api/models/provider_manager.py) | Resolves local or hosted providers and scopes activation to a request. |
| [`litellm/provider.py`](../../chatbot-core/api/models/litellm/provider.py) | Adapts LiteLLM completion and streaming calls to `LLMProvider`. |
| [`chatbot.py`](../../chatbot-core/api/routes/chatbot.py) | Exposes provider metadata and applies provider selection to REST, upload, and WebSocket routes. |
| [`Header.tsx`](../../frontend/src/components/Header.tsx) | Displays provider selection and API-key availability. |

---

## 5. Edge Cases Handled

- Invalid catalog JSON, duplicate IDs, blank fields, and unknown fields are rejected.
- Unknown provider IDs return an explicit error.
- Hosted providers without a key remain visible as unavailable.
- The local provider bypasses LiteLLM and does not require a key.
- Provider state is isolated per request so one request does not change the active provider for another.

---

## 6. How to Use It

To add DeepSeek V4 Flash, add this object to the `providers` array in
`chatbot-core/api/config/providers.json`:

```json
{
  "id": "deepseek",
  "label": "DeepSeek API",
  "model": "deepseek/deepseek-v4-flash"
}
```

Then:

1. Run `make sync-provider-env`.
2. Set `DEEPSEEK_API_KEY` in `chatbot-core/.env`.
3. Restart the backend.
4. Choose **DeepSeek API** in the chatbot selector.

Use a small prompt to confirm that the key and model route work before using a hosted provider for longer requests.

---

## 7. Troubleshooting

### Provider Is Missing

Check that `providers.json` is valid, the ID is unique, and the backend has been restarted. Then inspect `GET /api/chatbot/providers`.

### Provider Has a Warning Icon

The matching API-key environment variable is empty in the running backend process. Run `make sync-provider-env`, set the generated key in `chatbot-core/.env`, and restart the backend.

### Request Is Rejected

Confirm that the request uses a catalog ID and that the matching key is present. The API returns an error for an unknown provider or a hosted provider without a configured key.

### Provider Returns an Error

Verify the model identifier and key against that provider's current documentation. Quota, model availability, and rate limits are provider-side concerns and are not silently routed to another provider.

---

## 8. Current Boundaries and Future Improvements

The current integration uses local environment keys. It does not yet implement Jenkins Credentials, per-user keys, provider permissions, automatic catalog reloads, custom API bases, or per-provider token limits.

Future credential onboarding can prompt a user who selects an unconfigured provider and direct them to the relevant Jenkins Credentials page once that integration exists.
