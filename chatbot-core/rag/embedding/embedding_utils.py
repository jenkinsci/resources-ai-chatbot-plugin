"""
Utility functions for loading a sentence transformer model and embedding text documents.
"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def load_embedding_model():
    """
    Load the sentence transformer model for generating text embeddings.

    Returns:
        SentenceTransformer: The loaded embedding model.
    """
    print(f"Loading embedding model: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)

def embed_documents(texts, model, batch_size=32):
    """
    Embed a list of text documents into dense vector representations using the given model.

    Args:
        texts (List[str]): List of documents or text chunks to embed.
        model (SentenceTransformer): A loaded SentenceTransformer model.
        batch_size (int, optional): Number of documents to embed in parallel. Defaults to 32.

    Returns:
        List[np.ndarray]: A list of embedding vectors (one per input document).
    """
    print(f"Embedding {len(texts)} documents")
    return model.encode(texts, batch_size=batch_size, show_progress_bar=True)
