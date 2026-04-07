# Vector Store

The vector store module is responsible for building, saving, and loading a **FAISS index** along with associated metadata for later retrieval. All logic related to persistent vector storage lives in: `chatbot-core/rag/vectorstore/`

This phase follows the **embedding** step and precedes the **retrieval** phase. It stores the document embeddings in a FAISS **IVF (Inverted File) index** to allow fast approximate nearest-neighbor search. Indeed it trade-off some accuracy for a faster retrieval.

## Index Type

- **FAISS Index**: `IndexIVFFlat` with `L2` distance
- **Number of clusters (`nlist`)**
- **Number of clusters to probe during search (`nprobe`)** 
These are tunable hyperparameters. For the number of clusters faiss offers a guideline that can be found [here](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index). Given our use case the ideal would be to stay between 4 x sqrt(#vectors) and 16 x sqrt(#vectors).`nprobe` should be instead tuned.

## Script: `store_embeddings.py`

### Purpose

Embeds all preprocessed chunks, builds a FAISS index (`IndexIVFFlat`), and stores:
- The trained FAISS index to disk
- The metadata aligned to each vector

### To Run

> **Note**: Make sure you have installed all the dependencies listed in `requirements.txt`.
> To try out it is encouraged to comment out the most heavy chunk files(Jenkins Docs and Jenkins Plugin Docs) in `embed_chunks`, since embedding all the chunks is quite computationally heavy.

```bash
python rag/vectorstore/store_embeddings.py
```

This will:

- Load all processed chunk files
- Compute embeddings using the `all-MiniLM-L6-v2` SentenceTransformer model
- Build a FAISS IVF index (with `nlist=256`, `nprobe=20`)
- Save:
  - `faiss_index.idx` to `data/embeddings/`
  - `faiss_metadata.pkl` to `data/embeddings/`

## Script: `vectorstore_utils.py`

### Purpose

Provides utility functions for **saving and loading**:
- FAISS index files
- Metadata associated with each vector
