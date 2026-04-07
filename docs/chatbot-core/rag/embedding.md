# Embedding

The embedding-related scripts are located in: `chatbot-core/rag/embedding/`

This phase converts preprocessed and chunked text documents into dense vector representations using a transformer-based model. These embeddings are later stored in a vector database to support semantic search and retrieval for the chatbot.

> **Note**: These scripts are not standalone entry points and are used as utility modules by downstream indexing and retrieval components.

---

## Model Used

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`  
  This lightweight embedding model offers a good trade-off between speed and semantic performance. The vector's output dimension is 384.

---

## Script: `embed_chunks.py`

### Purpose

Loads all previously generated text chunks from the `processed/` directory, computes their embeddings using the selected model, and returns both:

- A list of embedding vectors
- The corresponding metadata (including code blocks)

## Script: `embedding_utils.py`

### Purpose

Provides utility functions for loading and using SentenceTransformer models.

#### Key Functions

- **`load_embedding_model(model_name, logger)`**  
  Loads a SentenceTransformer model by name.

- **`embed_documents(texts, model, logger, batch_size=32)`**  
  Encodes a list of text strings into dense vectors. Supports batching and shows a progress bar during embedding.
