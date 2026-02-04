.PHONY: all api setup-backend build-frontend test run-data-pipeline clean

BACKEND_SHELL = cd chatbot-core && . ./venv/bin/activate

ifeq ($(IS_CPU_REQ),1)
	REQUIREMENTS=requirements-cpu.txt
else
	REQUIREMENTS=requirements.txt
endif

all: build-frontend setup-backend run-api

setup-backend:
	@if [ ! -d chatbot-core/venv ]; then \
		cd chatbot-core && \
		python3 -m venv venv && \
		. venv/bin/activate && \
		pip install -r $(REQUIREMENTS); \
	else \
		echo "Backend already set up. Skipping virtualenv creation and dependencies installation."; \
	fi

build-frontend:
	@cd frontend && \
	npm install && \
	npm run build

# API

run-api:
	@$(BACKEND_SHELL) && PYTHONPATH=$$(pwd) uvicorn api.main:app --reload

api: setup-backend run-api

dev-lite: setup-backend
	@echo "Starting API in lite mode..."
	# Lite mode uses PYTEST_VERSION=1 to load the testing configuration,
	# which disables local LLM loading. This is useful for API development
	# when you don't need to test actual chat completions.
	@$(BACKEND_SHELL) && PYTEST_VERSION=1 PYTHONPATH=$$(pwd) uvicorn api.main:app --reload

# TESTS

run-frontend-tests:
	@cd frontend && \
	npm install && \
	echo "### RUNNING FRONTEND TESTS ###" && \
	npm run test

run-backend-tests: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### RUNNING BACKEND UNIT TESTS ###" && \
	PYTHONPATH=$$(pwd) pytest tests/unit && \
	echo "### RUNNING BACKEND INTEGRATION TESTS ###" && \
	PYTHONPATH=$$(pwd) pytest tests/integration

run-test: run-frontend-tests run-backend-tests

# DATA PIPELINE

## DATA COLLECTION

run-data-collection-docs: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### COLLECTING JENKINS DOCS ###" && \
	python3 data/collection/docs_crawler.py

run-data-collection-plugins: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### COLLECTING JENKINS PLUGIN DOCS ###" && \
	echo "### 1. FETCHING PLUGIN NAMES LIST ###" && \
	python3 data/collection/fetch_list_plugins.py && \
	echo "### 2. FETCHING PLUGIN DOCS ###" && \
	python3 data/collection/jenkins_plugins_fetch.py

run-data-collection-discourse: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### COLLECTING DISCOURSE THREADS ###" && \
	echo "### 1. FETCHING DISCOURSE TOPICS ###" && \
	python3 data/collection/discourse_topics_retriever.py && \
	echo "### 2. FILTERING DISCOURSE TOPICS ###" && \
	python3 data/collection/collection_utils/filter_discourse_threads.py && \
	echo "### 3. FETCHING DISCOURSE POSTS FOR FILTERED TOPICS ###" && \
	python3 data/collection/discourse_fetch_posts.py

run-data-collection: run-data-collection-docs run-data-collection-plugins run-data-collection-discourse

## DATA PREPROCESSING

run-data-preprocessing-docs: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### PREPROCESSING JENKINS DOCS ###" && \
	echo "### 1. PROCESSING JENKINS DOCS ###" && \
	python3 data/preprocessing/preprocess_docs.py && \
	echo "### 2. FILTERING PROCESSED JENKINS DOCS ###" && \
	python3 data/preprocessing/filter_processed_docs.py

run-data-preprocessing-plugins: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### PREPROCESSING JENKINS PLUGIN DOCS ###" && \
	python3 data/preprocessing/preprocess_plugin_docs.py

run-data-preprocessing: run-data-preprocessing-docs run-data-preprocessing-plugins

## DATA CHUNKING

run-data-chunking-docs: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### CHUNKING JENKINS DOCS ###" && \
	python3 data/chunking/extract_chunk_docs.py

run-data-chunking-plugins: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### CHUNKING JENKINS PLUGIN DOCS ###" && \
	python3 data/chunking/extract_chunk_plugins.py

run-data-chunking-discourse: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### CHUNKING DISCOURSE THREADS ###" && \
	python3 data/chunking/extract_chunk_discourse.py

run-data-chunking-stack: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### CHUNKING STACKOVERFLOW THREADS ###" && \
	python3 data/chunking/extract_chunk_stack.py

run-data-chunking: run-data-chunking-docs run-data-chunking-plugins run-data-chunking-discourse run-data-chunking-stack

## EMBEDDING & STORAGE

run-data-storage: setup-backend
	@$(BACKEND_SHELL) && \
	echo "### EMBEDDING AND STORING THE CHUNKS ###" && \
	python3 data/rag/vectorstore/store_embeddings.py


run-pipeline-core: run-data-collection run-data-preprocessing run-data-chunking run-data-storage

run-data-pipeline:
	@echo "Logging data pipeline to logs/data-pipeline.log"
	@mkdir -p logs
	@sleep 3
	@$(MAKE) run-pipeline-core > logs/data-pipeline.log 2>&1

# CLEAN

clean:
	@rm -rf chatbot-core/venv frontend/node_modules
