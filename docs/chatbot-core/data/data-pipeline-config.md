# Data Pipeline Configuration Guide

## Overview

The Jenkins AI Chatbot data pipeline now uses a centralized YAML configuration file located at `chatbot-core/config/data-pipeline.yml`. This configuration centralizes all tunable parameters for the collection, preprocessing, chunking, embedding, and storage phases of the pipeline.

## Benefits

- **Single Source of Truth**: All pipeline parameters in one place
- **Easy Tuning**: Modify parameters without editing Python code
- **Environment Flexibility**: Override settings via environment variables

## Usage

### Basic Usage with Default Config

```bash
# Run entire pipeline with default config
make run-data-pipeline
```

### Using Custom Config

```bash
# Specify custom config path
make run-data-pipeline CONFIG_PATH=/path/to/my-config.yml
```

### Environment Overrides

```bash
# Override chunk size
export CHUNK_SIZE=700
make run-data-chunking
```

**Supported Overrides:**
- `CHUNK_SIZE`: Override chunking.chunk_size
- `CHUNK_OVERLAP`: Override chunking.chunk_overlap
- `EMBEDDING_MODEL`: Override embedding.model_name
- `FAISS_N_LIST`: Override storage.n_list
- `FAISS_N_PROBE`: Override storage.n_probe

## See Also

- [Chunking Documentation](./chunking.md)
- [Collection Documentation](./collection.md)
- [Preprocessing Documentation](./preprocessing.md)
