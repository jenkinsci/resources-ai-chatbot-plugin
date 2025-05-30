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
  - `requirements.txt`: Python dependencies.
- `docs/`: Developer documentation.

## Setup Instructions

> **Note**:
> Please use **Python 3.11 or later**. Ensure your installation includes support for the `venv` module.

To set up the environment and run the scripts:

1. Navigate to the `chatbot-core` directory:
    ```bash
    cd chatbot-core
    ```

2. Create a Python virtual environment
    ```bash
    python3 -m venv venv
    ```

3. Activate the virtual environment
    - Linux/macOS
        ```bash
        source venv/bin/activate
        ```
    - Windows
        ```bash
        .\venv\Scripts\activate
        ```
4. Install the dependencies
    ```bash
    pip install -r requirements.txt
    ```

## Data Collection

The data collection scripts are located under:

```
chatbot-core/data/collection/
```

These scripts gather information from three key sources:
- Jenkins official documentation
- Discourse community topics
- StackOverflow threads

This section describes how to run the individual data collection scripts for each source. The results will be stored in the `raw` directory.

---

### Jenkins Documentation

The script `docs_crawler.py` recursively crawls the [Jenkins official documentation](https://www.jenkins.io/doc/) starting from the base URL. It collects the main content from each documentation page and stores it in a structured JSON file.

- **Input**: No input required — the script starts crawling from the base documentation URL.
- **Output**: A `jenkins_docs.json` file saved under `chatbot-core/data/raw/`, containing page URLs as keys and their HTML content as values.

**To run:**

```bash
python data/collection/docs_crawler.py
```

> **Note**: Make sure you're in the chatbot-core directory and your virtual environment is activated before running this or any script.

### Discourse Topics

This data collection pipeline fetches community discussions from the [Jenkins Discourse forum](https://community.jenkins.io) under the "Using Jenkins" category. It runs in **three steps**, using separate scripts:

#### 1. Fetch topic list

**Script**: `discourse_topics_retriever.py`

Fetches all topics under the "Using Jenkins" category(including sub-category "Ask a question").

- **Input**: None — it exploits the Discourse API.
- **Output**: `discourse_topic_list.json` (stored in `chatbot-core/data/raw/`)

**To run:**
```bash
python data/collection/discourse_topics_retriever.py
```

#### 2. Filter topics

**Script**: `utils/filter_discourse_threads.py`

Filters the previously collected topics, keeping only those with an accepted answer.

- **Input**: `discourse_topic_list.json`
- **Output**: `filtered_discourse_topics.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/utils/filter_discourse_threads.py
```

#### 3. Fetch post content

**Script**: `discourse_fetch_posts.py`

Fetches all post content for each filtered topic, including the question and all replies.

- **Input**: `filtered_discourse_topics.json` 
- **Output**: `topics_with_posts.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/discourse_fetch_posts.py
```

### StackOverflow Threads

This script processes data collected manually from StackOverflow using [StackExchange Data Explorer](https://data.stackexchange.com/stackoverflow/query/new). The query retrieves the top 1000 Jenkins-related threads with accepted answers, positive scores, and created in or after 2020.

#### 1. Export the CSV from StackExchange

Run the following SQL query in the [StackExchange Data Explorer](https://data.stackexchange.com/stackoverflow/query/new) to export a list of high-quality Jenkins-related threads:

```sql
SELECT TOP 1000
    q.Id AS [Question ID],
    q.Title AS [Question Title],
    q.Body AS [Question Body],
    q.Tags AS [Tags],
    q.CreationDate,
    q.Score AS [Question Score],
    a.Id AS [Accepted Answer ID],
    a.Score AS [Answer Score],
    a.Body AS [Answer Body]
FROM Posts q
INNER JOIN Posts a ON q.AcceptedAnswerId = a.Id
WHERE
    q.Tags LIKE '%<jenkins>%'
    AND q.Score >= 1
    AND q.CreationDate >= '2020-01-01'
ORDER BY q.Score DESC
```

The result can be downloaded as aCSV file and have to be placed in the following path: ```chatbot-core/data/raw/QueryResults.csv```

#### 2. Convert CSV to JSON

**Script**: `utils/convert_stack_threads.py`

This script reads the exported CSV and converts it into a JSON format. The resulting JSON file will contain a list of question-answer pairs with metadata.

- **Input**: `QueryResults.csv` 
- **Output**: `stack_overflow_threads.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/utils/convert_stack_threads.py
```
### Jenkins Plugins

This pipeline fetches the documentation content of the Jenkins plugins hosted on [https://plugins.jenkins.io/](https://plugins.jenkins.io/).

The collection process consists of two main scripts:

#### 1. Retrieve plugin names

**Script**: `fetch_list_plugins.py`

Fetches the list of all available plugins from the [Jenkins update site](https://updates.jenkins.io/experimental/latest/) and saves their names (without `.hpi` extension).

- **Output**: `plugin_names.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/fetch_list_plugins.py
```

#### 2. Fetch plugin documentation

**Script**: `jenkins_plugin_fetch.py`

Uses the list of plugin names to fetch documentation content from each plugin's page on [plugins.jenkins.io](https://plugins.jenkins.io). It extracts the main `<div class="content">` section from each page, which contains the content we are interested in.

- **Input**: `plugin_names.json`
- **Output**: `plugin_docs.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/jenkins_plugin_fetch.py
```

## Data Preprocessing

After collecting raw documentation from the different sources, a preprocessing step is required to extract the main content, clean from undesired HTML tags, and remove low-value or noisy entries. This step ensures the chatbot receives clean, relevant text data.

---

### Jenkins Documentation

#### 1. `preprocess_docs.py`

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

#### 2. `filter_processed_docs.py`

This script performs a final filtering pass on the preprocessed Jenkins documentation to remove low-quality or irrelevant pages before indexing.

##### Purpose

After the HTML content is cleaned by `preprocess_docs.py`, this script removes:

- Pages with **fewer than 300 visible characters** (e.g. stubs, placeholders)
- Pages with a **high link-to-text ratio** (indicating index pages or link hubs)

Pages with `/extensions` in the URL are excluded from filtering and always retained.

##### How It Works

- Combines both `developer_docs` and `non_developer_docs` from `processed_jenkins_docs.json`
- Normalizes all URLs (removes `index.html` and trailing slashes)
- For each page:
  - Computes visible text length
  - Calculates link-to-text ratio
  - Filters pages failing the threshold

**Input**: `processed_jenkins_docs.json`: Cleaned docs with developer and non-developer sections.

**Output**: `filtered_jenkins_docs.json`: Final cleaned dictionary of relevant Jenkins documentation. (stored in `chatbot-core/data/processed`)

##### To run:
```bash
python data/preprocessing/filter_processed_docs.py
```

> **Note**: The HTML structure is preserved at this stage. It may be useful for extracting metadata (e.g. headings, lists) or applying chunking strategies. Full conversion to plain text is deferred to a later phase in the pipeline.

#### Extra. `utils/` (Utility Package)

This package contains shared utility functions used across the preprocessing scripts. It includes helpers for:

- Extracting and cleaning HTML content
- Normalizing URLs
- Filtering based on content structure and quality

These utilities are used by both `preprocess_docs.py` and `filter_processed_docs.py` to keep the logic modular and reusable. The functions are exposed through `utils/__init__.py` for easier imports across scripts.

### Jenkins Plugin Docs

#### 1. `preprocess_plugin_docs.py`

This script processes the raw plugin documentation collected from [plugins.jenkins.io](https://plugins.jenkins.io) and prepares it for downstream use by cleaning the HTML and filtering out trivial entries.

##### Purpose

The plugin docs contain a wide range of formats and often include boilerplate or short descriptions. This script ensures only meaningful documentation is kept by:

- Removing unwanted HTML tags (e.g. `<img>`, `<script>`, etc.)
- Stripping out all HTML comments
- Filtering out entries with fewer than 60 visible text characters


**Input**: `plugin_docs.json`: Raw HTML content for each plugin page.

**Output**: `processed_plugin_docs.json`: Cleaned and filtered plugin documentation. (stored in `chatbot-core/data/processed`)

##### To run:
```bash
python data/preprocessing/preprocess_plugin_docs.py
```

> **Note**: The HTML structure is preserved at this stage. It may be useful for extracting metadata (e.g. headings, lists) or applying chunking strategies. Full conversion to plain text is deferred to a later phase in the pipeline.

### Discourse Topics

Since the filtering and cleanup of threads happen during collection, no additional preprocessing is required at this stage. Enriching the threads with metadata or preparing them for vectorization will be done during the chunking stage.

### StackOverflow Threads

At this stage, no additional preprocessing is needed. The content is already filtered for accepted answers, scored positively, and includes only Jenkins-related threads. Further processing will occur during the chunking phase.
