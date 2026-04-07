# Data Preprocessing

After collecting raw documentation from the different sources, a preprocessing step is required to extract the main content, clean from undesired HTML tags, and remove low-value or noisy entries. This step ensures the chatbot receives clean, relevant text data.

---

## Jenkins Documentation

### 1. `preprocess_docs.py`

This script filters and extracts the main content from each raw Jenkins doc page.

- **Input**: `jenkins_docs.json`  
- **Output**: `processed_jenkins_docs.json` (stored in `chatbot-core/data/processed`)

It separates documentation into:
- **Developer docs** (content in `col-8` containers)
- **Non-developer docs** (content in `col-lg-9` containers)

Each page is cleaned by:
- Extracting only the main content container
- Removing table of contents (`.toc`), `<script>`, `<img>`, and similar tags
- Stripping navigation blocks (non-developer only)
- Removing all HTML comments

**To run:**
```bash
python data/preprocessing/preprocess_docs.py
```

### 2. `filter_processed_docs.py`

This script performs a final filtering pass on the preprocessed Jenkins documentation to remove low-quality or irrelevant pages before indexing.

#### Purpose

After the HTML content is cleaned by `preprocess_docs.py`, this script removes:

- Pages with **fewer than 300 visible characters** (e.g. stubs, placeholders)
- Pages with a **high link-to-text ratio** (indicating index pages or link hubs)

Pages with `/extensions` in the URL are excluded from filtering and always retained.

#### How It Works

- Combines both `developer_docs` and `non_developer_docs` from `processed_jenkins_docs.json`
- Normalizes all URLs (removes `index.html` and trailing slashes)
- For each page:
  - Computes visible text length
  - Calculates link-to-text ratio
  - Filters pages failing the threshold

**Input**: `processed_jenkins_docs.json`: Cleaned docs with developer and non-developer sections.

**Output**: `filtered_jenkins_docs.json`: Final cleaned dictionary of relevant Jenkins documentation. (stored in `chatbot-core/data/processed`)

#### To run:
```bash
python data/preprocessing/filter_processed_docs.py
```

> **Note**: The HTML structure is preserved at this stage. It may be useful for extracting metadata (e.g. headings, lists) or applying chunking strategies. Full conversion to plain text is deferred to a later phase in the pipeline.

### Extra. `utils/` (Utility Package)

This package contains shared utility functions used across the preprocessing scripts. It includes helpers for:

- Extracting and cleaning HTML content
- Normalizing URLs
- Filtering based on content structure and quality

These utilities are used by both `preprocess_docs.py` and `filter_processed_docs.py` to keep the logic modular and reusable. The functions are exposed through `utils/__init__.py` for easier imports across scripts.

## Jenkins Plugin Docs

### 1. `preprocess_plugin_docs.py`

This script processes the raw plugin documentation collected from [plugins.jenkins.io](https://plugins.jenkins.io) and prepares it for downstream use by cleaning the HTML and filtering out trivial entries.

#### Purpose

The plugin docs contain a wide range of formats and often include boilerplate or short descriptions. This script ensures only meaningful documentation is kept by:

- Removing unwanted HTML tags (e.g. `<img>`, `<script>`, etc.)
- Stripping out all HTML comments
- Filtering out entries with fewer than 60 visible text characters


**Input**: `plugin_docs.json`: Raw HTML content for each plugin page.

**Output**: `processed_plugin_docs.json`: Cleaned and filtered plugin documentation. (stored in `chatbot-core/data/processed`)

#### To run:
```bash
python data/preprocessing/preprocess_plugin_docs.py
```

> **Note**: The HTML structure is preserved at this stage. It may be useful for extracting metadata (e.g. headings, lists) or applying chunking strategies. Full conversion to plain text is deferred to a later phase in the pipeline.

## Discourse Topics

Since the filtering and cleanup of threads happen during collection, no additional preprocessing is required at this stage. Enriching the threads with metadata or preparing them for vectorization will be done during the chunking stage.

## StackOverflow Threads

At this stage, no additional preprocessing is needed. The content is already filtered for accepted answers, scored positively, and includes only Jenkins-related threads. Further processing will occur during the chunking phase.
