## Retriever

The retriever module enables querying the FAISS vector index to find the most semantically relevant document chunks based on a natural language input. This phase is responsible for fetching context-rich results from the indexed embedding space, which are then used to inform the chatbot’s responses.

All related scripts are located under: `chatbot-core/rag/retriever/`

### Script: `retrieve.py`

#### Purpose

Given a query string, this script:
- Loads the same SentenceTransformer model used during indexing
- Loads the FAISS vector index and associated metadata
- Embeds the query into a vector
- Searches the index to retrieve the top `k` most relevant chunks
- Returns the matched results and their similarity scores

> **Note**: This script is not meant to be executed directly, but rather imported and called from another module

### Script: `retriever_utils.py`

#### Purpose

Provides helper functions for:
- Loading the FAISS index and associated metadata from disk
- Performing vector search using a query embedding
