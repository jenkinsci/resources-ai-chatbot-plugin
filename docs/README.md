# Documentation for Jenkins Chatbot Plugin

This documentation folder contains resources and instructions related to the development of the RAG-based chatbot plugin for Jenkins.

## Directory Structure

Below is a brief explanation of the key subdirectories:

- `chatbot-core/`: Core logic of the chatbot.
  - `data/`: Data-related files and scripts.
    - `collection/`: Scripts to collect data from Jenkins Docs, Jenkins Plugins, Discourse, StackOverflow.
    - `preprocessing/`: Scripts to clean, filter, the collected data before chunking.
    - `raw/`: Output directory for collected data.
    - `processed/`: Output directory for cleaned and filtered data.
  - `utils/`: Contains utils for the chatbot-core directory(e.g. logger).
  - `rag/`: Core logic of the RAG
    - `embedding/`: Scripts to embed the chunks.
    - `vectorestore/`: Scripts to store the embeddings into a vector database.
    - `retrieval/`: Scripts to perform the semantic research across the vectore database.
  - `api/`: FastAPI application that exposes the chatbot via a REST API.
    - `main.py`: Entry point to run the FastAPI app.
    - `routes/`: Defines the HTTP endpoints.
    - `services/`: Contains the business logic, representing the service layer .
    - `models/`: Contains schemas and LLM interface.
    - `prompts/`: Utilities for prompt formatting and construction.
    - `config/`: Loads and provides application configuration (YAML-based).
  - `tests/`: Tests for the backend.
    - `unit/`: Contains the unit tests and the related configuration.
    - `integration/`: Contains the integration tests and the related configuration.
  - `requirements.txt`: Python dependencies.
  - `requirements-cpu.txt`: Python dependencies for cpu only usage.
- `docs/`: Developer documentation. Inside it mirros the codebase layout.
- `frontend/`: Directory for the frontend React application.

## Getting Started

To quickly start, in the root directory a `Makefile` contains many ready-to-go targets, that allow to run basic flows(e.g. running the API).

In this doc file we'll use these targets, without going into the details of the scripts and the implementation reasonings. For further information you can visit the package-related doc files.

For the setup you can follow [Setup Guide](setup.md).

## Data Pipeline

The first thing we want to be able to do is running the whole data pipeline. The data pipeline comprehends the following phases:

- Data Collection
- Preprocessing
- Chunking
- Embedding
- Storage

> **Note:** the collection of StackOverflow's data is not included; to include it you must follow [this](chatbot-core/data/collection.md).

So starting from the identificatiion of the data sources(e.g. Jenkins Official Documentation) the data pipeline will collect it, process it, and finally store it in a vector database(FAISS) to later perform semantic search.

To run the following pipeline you can use the `run-data-pipeline` target:

```bash
make run-data-pipeline
```

> **Note:** for more details on the scripts and on the single processes you can visit the docs under `docs/chatbot-core/data/` and `docs/chatbot-core/rag/`.

### Centralized Configuration

All tunable parameters for collection, preprocessing, chunking, embedding, and storage are managed via a centralized YAML file: `chatbot-core/config/data-pipeline.yml`.

- View the schema and guidance: `docs/chatbot-core/data/data-pipeline-config.md`
- Override the config per run via Makefile:

```bash
make run-data-pipeline CONFIG_PATH=chatbot-core/config/data-pipeline.yml
```

You can also override critical parameters using environment variables (e.g., `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_MODEL`, `FAISS_N_LIST`, `FAISS_N_PROBE`). See the configuration guide for details.

## API

Another key component in this repo is the backend, that allows to run the API that serves the chabot funcionalities. Also for the API there is a specific target in the `Makefile`, that does all the setup, installing the correct dependencies in the virtual environment, and runs the API.

To run it you can use the `api` target:

```bash
make api
```

> **Note:** for more details on the API and on the architectual overview you can visit the docs under `docs/chatbot-core/api/`.

## User Interface

For the UI the project relies on a React application, that is then built and injected into the Jenkins UI. A target in the `Makefile` allows to run the flow that builds the React app.

You can do that by running:

```bash
make build-frontend
```

After running this command you can run Jenkins (`mvn hpi:run`).

> **Note:** for more details on the frontend you can visit the docs under `docs/frontend/`.

## Tests

For both the frontend and the backend we have a suite of unit and integration tests. Also in this case we have a specific target to run all the tests.

To run the tests:

```bash
make run-test
```
