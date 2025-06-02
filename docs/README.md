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
  - `requirements.txt`: Python dependencies.
- `docs/`: Developer documentation.
- `frontend/`: Directory for the frontend React application.

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
5. Set the `PYTHONPATH` to the current directory(`chatbot-core/`):
    ```bash
    export PYTHONPATH=$(pwd)
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

**Script**: `collection_utils/filter_discourse_threads.py`

Filters the previously collected topics, keeping only those with an accepted answer.

- **Input**: `discourse_topic_list.json`
- **Output**: `filtered_discourse_topics.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/collection_utils/filter_discourse_threads.py
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

**Script**: `collection_utils/convert_stack_threads.py`

This script reads the exported CSV and converts it into a JSON format. The resulting JSON file will contain a list of question-answer pairs with metadata.

- **Input**: `QueryResults.csv` 
- **Output**: `stack_overflow_threads.json` (stored in `chatbot-core/data/raw`)

**To run:**
```bash
python data/collection/collection_utils/convert_stack_threads.py
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

## Chunking

After collecting and preprocessing the raw content from various sources, the next step in the RAG pipeline is **chunking**. This phase involves splitting the cleaned text into smaller, semantically meaningful units that are suitable for embedding and retrieval by the chatbot.

All chunking scripts are located under the directory:`chatbot-core/data/chunking/`


Below are the chunking procedures for each data source.

---

### Jenkins Documentation

#### Script: `extract_chunk_docs.py`

This script performs chunking on the Jenkins documentation using a recursive splitting strategy and enriches the chunks with extracted code blocks and metadata.

- **Input**:  
  `filtered_jenkins_docs.json` — Preprocessed Jenkins documentation (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_docs.json` — Chunked documentation with metadata and code snippets (stored in `chatbot-core/data/processed/`)

#### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are approximately **500 characters long** with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splitting is done using a hierarchy of separators: `\n\n`, `\n`, space, and character level.

#### Code Block Handling

- Code blocks are extracted from `<pre>` tags using BeautifulSoup.
- The script attempts to reassign these code snippets to the most relevant text chunks using a regex-based system.
- Each chunk includes a list of its associated `code_blocks`.

#### Metadata Included in Each Chunk

- `chunk_text`: The chunked text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_documentation"`
  - `source_url`: URL of the original documentation page.
  - `title`: Extracted page title.
- `code_blocks`: Extracted code snippets relevant to this chunk.

#### To run:

```bash
python data/chunking/extract_chunk_docs.py
```
> **Note**:
> Ensure `langchain` and the other dependencies in the `requirements.txt` are met in your environment.

### Jenkins Plugin Documentation

#### Script: `extract_chunk_plugins.py`

This script processes the pre-cleaned plugin documentation and splits it into consistent text chunks. It also extracts and associates code blocks with the corresponding text segments when available.

- **Input**:  
  `processed_plugin_docs.json` — Cleaned plugin documentation HTML (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_plugin_docs.json` — A list of chunked plugin docs with associated metadata (stored in `chatbot-core/data/processed/`)

#### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are roughly **500 characters** long with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splits text using prioritized separators: paragraph breaks (`\n\n`), single newlines (`\n`), spaces, and individual characters.

#### Code Block Handling

- `<pre>` tags are parsed using BeautifulSoup to extract code snippets.
- Extracted blocks are reattached to the most relevant chunk using a positional and regex marker strategy.
- Each chunk includes a `code_blocks` field listing relevant snippets.

#### Metadata Included in Each Chunk

- `chunk_text`: The chunked body of text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_plugins_documentation"`
  - `title`: Plugin name as inferred from the source key.
- `code_blocks`: Any code blocks found in the original plugin doc and matched to this chunk.

#### To run:

```bash
python data/chunking/extract_chunk_plugins.py
```

### Discourse Topics

#### Script: `extract_chunk_discourse.py`

This script processes cleaned Discourse threads by concatenating the posts, extracting code snippets, and splitting the text into semantically coherent chunks. It preserves conversational flow while enriching each chunk with contextual metadata.

- **Input**:  
  `topics_with_posts.json` — A list of Discourse threads with collected question and answer posts (found in `chatbot-core/data/raw/`)

- **Output**:  
  `chunks_discourse_docs.json` — List of processed thread chunks, stored in `chatbot-core/data/processed/`

#### Chunking Strategy

- Combines all posts from a thread into a single text block.
- Uses `RecursiveCharacterTextSplitter` from LangChain to split the content into chunks of roughly **500 characters** with **100 characters overlap**.
- Text is chunked using prioritized separators: double newline, single newline, space, and then character-level.

#### Code Block Handling

- The script identifies both:
  - **Multiline code blocks** 
  - **Inline code snippets**
- Code blocks are identified using regex patterns.
- Code blocks are replaced with placeholder tokens before chunking.
- Code blocks are listed under the `code_blocks` field in each chunk.

#### Metadata Included in Each Chunk

- `chunk_text`: The text content of the chunk.
- `metadata`: Includes:
  - `data_source`: `"discourse_threads"`
  - `topic_id`: Discourse topic ID
  - `title`: Title of the thread
- `code_blocks`: Extracted code snippets from the thread text, if any.

#### To run:

```bash
python data/chunking/extract_chunk_discourse.py
```

### StackOverflow Threads

#### Script: `extract_chunk_stack.py`

This script takes the filtered StackOverflow data, parses the HTML from both questions and answers, extracts code snippets, and chunks the content into structured units.

- **Input**:  
  `stack_overflow_threads.json` — Contains structured Q&A pairs with metadata, located in `chatbot-core/data/raw/`

- **Output**:  
  `chunks_stackoverflow_threads.json` — A list of chunked question-answer pairs, saved in `chatbot-core/data/processed/`

#### Chunking Strategy

- Questions and accepted answers are concatenated into a single text block.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Uses `RecursiveCharacterTextSplitter` from LangChain to generate chunks:
  - **500 characters per chunk**
  - **100 character overlap**
  - Splitting hierarchy: paragraph (`\n\n`), newline (`\n`), space, and character.

#### Code Block Handling

- Extracts `<code>` blocks from the HTML content.
- Code blocks are temporarily replaced with placeholders (the format is defined by `PLACEHOLDER_TEMPLATE`; e.g `[[CODE_BLOCK_n]]`) before chunking.
- Post-chunking, the placeholders are matched back to their original code snippets and added under `code_blocks`.

#### Metadata Included in Each Chunk

- `chunk_text`: Combined question and answer content, chunked.
- `metadata`: Includes:
  - `data_source`: `"stackoverflow_threads"`,
  - `question_id`: StackOverflow question ID
  - `title`: Question title
  - `tags`: StackOverflow tags
  - `creation_date`: Question creation date
  - `question_score`: Score of the question
  - `answer_score`: Score of the accepted answer
- `code_blocks`: Relevant code blocks extracted from the thread

#### To run:

```bash
python data/chunking/extract_chunk_stack.py
```

### Utility Functions

Several of the chunking scripts rely on shared helper functions to handle common tasks such as code block extraction, chunk-to-code matching, and title parsing. These utilities are defined in:`chatbot-core/data/chunking/utils/`.

## User Inteface

The chatbot UI is built using the following technologies:

- **Framework**: _React_
- **Language**: _TypeScript_
- **Build Tool**: _Vite_

### Directory Structure (`/frontend`)

- `frontend/`
  - `src/`
    - `api/`: API utilities for backend communication
    - `components/`: React components
    - `data/`: Static text used in the UI
    - `model/`: TypeScript interfaces and types
    - `styles/`: Style definitions
  - `dist/`: Build output generated by Vite (ignored in Git)
  - `vite.config.ts`: Vite configuration file
  - `package.json`: NPM metadata and scripts

### Setup and Use
> **Note**:  
> It is encouraged to use the latest**Node.js LTS** (project built with Node 24).  
> Ensure `npm` is available in your environment.

To build and run the frontend as part of the Jenkins plugin:

1. Navigate to the frontend directory:
    ```bash
    cd frontend
    ```

2. Install dependencies:
    ```bash
    npm install
    ```

3. Build the frontend and copy the output to Jenkins:
    ```bash
    npm run build
    ```

    This command builds the frontend using Vite and copies the compiled assets to:

    ```
    src/main/webapp/static/
    ```

4. Move back to the project root and start Jenkins:
    ```bash
    cd ..
    mvn hpi:run
    ```

### Using the Chatbot in Jenkins

Once Jenkins is running:

- Look for a 💬 button in the **bottom-right corner**.
- Click it to toggle the chatbot panel.
- You can:
  - Type or paste questions (supports multiline)
  - Press `Enter` to send
  - Press `Shift + Enter` for a new line
  - Clear the conversation with the **"Clear chat"** button in the header
- Messages **persist on page refresh** (within the same session) but are **cleared when the tab or browser is closed**.

### UI Integration in Jenkins

To inject the React-based chatbot into the Jenkins interface, the plugin uses a `PageDecorator` extension along with a Jelly template. In this way the chatbot is injected globally across all pages in Jenkins.

#### `ChatbotGlobalDecorator.java`

This java file is placed in:

```
src/main/java/io/jenkins/plugins/chatbot/ChatbotGlobalDecorator.java
```

The `ChatbotGlobalDecorator` is a Jenkins extension that allows injecting custom HTML or scripts into the global page layout.

This registers a decorator that looks for a corresponding Jelly template to render additional content on all pages.

#### Jelly: `footer.jelly`

The Jelly file is placed in:

```
src/main/resources/io/jenkins/plugins/chatbot/ChatbotGlobalDecorator/footer.jelly
```

Its purpose is to inject the React root element and the compiled JavaScript bundle (built with Vite) into the page:

- `<div id="chatbot-root"></div>` serves as the mount point for the React application.
- The script loads the compiled JavaScript file from the plugin's static resources:
  ```
  src/main/webapp/static/assets/index.js
  ```

## Chunking

After collecting and preprocessing the raw content from various sources, the next step in the RAG pipeline is **chunking**. This phase involves splitting the cleaned text into smaller, semantically meaningful units that are suitable for embedding and retrieval by the chatbot.

All chunking scripts are located under the directory:`chatbot-core/data/chunking/`


Below are the chunking procedures for each data source.

---

### Jenkins Documentation

#### Script: `extract_chunk_docs.py`

This script performs chunking on the Jenkins documentation using a recursive splitting strategy and enriches the chunks with extracted code blocks and metadata.

- **Input**:  
  `filtered_jenkins_docs.json` — Preprocessed Jenkins documentation (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_docs.json` — Chunked documentation with metadata and code snippets (stored in `chatbot-core/data/processed/`)

#### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are approximately **500 characters long** with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splitting is done using a hierarchy of separators: `\n\n`, `\n`, space, and character level.

#### Code Block Handling

- Code blocks are extracted from `<pre>` tags using BeautifulSoup.
- The script attempts to reassign these code snippets to the most relevant text chunks using a regex-based system.
- Each chunk includes a list of its associated `code_blocks`.

#### Metadata Included in Each Chunk

- `chunk_text`: The chunked text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_documentation"`
  - `source_url`: URL of the original documentation page.
  - `title`: Extracted page title.
- `code_blocks`: Extracted code snippets relevant to this chunk.

#### To run:

```bash
python data/chunking/extract_chunk_docs.py
```
> **Note**:
> Ensure `langchain` and the other dependencies in the `requirements.txt` are met in your environment.

### Jenkins Plugin Documentation

#### Script: `extract_chunk_plugins.py`

This script processes the pre-cleaned plugin documentation and splits it into consistent text chunks. It also extracts and associates code blocks with the corresponding text segments when available.

- **Input**:  
  `processed_plugin_docs.json` — Cleaned plugin documentation HTML (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_plugin_docs.json` — A list of chunked plugin docs with associated metadata (stored in `chatbot-core/data/processed/`)

#### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are roughly **500 characters** long with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splits text using prioritized separators: paragraph breaks (`\n\n`), single newlines (`\n`), spaces, and individual characters.

#### Code Block Handling

- `<pre>` tags are parsed using BeautifulSoup to extract code snippets.
- Extracted blocks are reattached to the most relevant chunk using a positional and regex marker strategy.
- Each chunk includes a `code_blocks` field listing relevant snippets.

#### Metadata Included in Each Chunk

- `chunk_text`: The chunked body of text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_plugins_documentation"`
  - `title`: Plugin name as inferred from the source key.
- `code_blocks`: Any code blocks found in the original plugin doc and matched to this chunk.

#### To run:

```bash
python data/chunking/extract_chunk_plugins.py
```

### Discourse Topics

#### Script: `extract_chunk_discourse.py`

This script processes cleaned Discourse threads by concatenating the posts, extracting code snippets, and splitting the text into semantically coherent chunks. It preserves conversational flow while enriching each chunk with contextual metadata.

- **Input**:  
  `topics_with_posts.json` — A list of Discourse threads with collected question and answer posts (found in `chatbot-core/data/raw/`)

- **Output**:  
  `chunks_discourse_docs.json` — List of processed thread chunks, stored in `chatbot-core/data/processed/`

#### Chunking Strategy

- Combines all posts from a thread into a single text block.
- Uses `RecursiveCharacterTextSplitter` from LangChain to split the content into chunks of roughly **500 characters** with **100 characters overlap**.
- Text is chunked using prioritized separators: double newline, single newline, space, and then character-level.

#### Code Block Handling

- The script identifies both:
  - **Multiline code blocks** 
  - **Inline code snippets**
- Code blocks are identified using regex patterns.
- Code blocks are replaced with placeholder tokens before chunking.
- Code blocks are listed under the `code_blocks` field in each chunk.

#### Metadata Included in Each Chunk

- `chunk_text`: The text content of the chunk.
- `metadata`: Includes:
  - `data_source`: `"discourse_threads"`
  - `topic_id`: Discourse topic ID
  - `title`: Title of the thread
- `code_blocks`: Extracted code snippets from the thread text, if any.

#### To run:

```bash
python data/chunking/extract_chunk_discourse.py
```

### StackOverflow Threads

#### Script: `extract_chunk_stack.py`

This script takes the filtered StackOverflow data, parses the HTML from both questions and answers, extracts code snippets, and chunks the content into structured units.

- **Input**:  
  `stack_overflow_threads.json` — Contains structured Q&A pairs with metadata, located in `chatbot-core/data/raw/`

- **Output**:  
  `chunks_stackoverflow_threads.json` — A list of chunked question-answer pairs, saved in `chatbot-core/data/processed/`

#### Chunking Strategy

- Questions and accepted answers are concatenated into a single text block.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Uses `RecursiveCharacterTextSplitter` from LangChain to generate chunks:
  - **500 characters per chunk**
  - **100 character overlap**
  - Splitting hierarchy: paragraph (`\n\n`), newline (`\n`), space, and character.

#### Code Block Handling

- Extracts `<code>` blocks from the HTML content.
- Code blocks are temporarily replaced with placeholders (the format is defined by `PLACEHOLDER_TEMPLATE`; e.g `[[CODE_BLOCK_n]]`) before chunking.
- Post-chunking, the placeholders are matched back to their original code snippets and added under `code_blocks`.

#### Metadata Included in Each Chunk

- `chunk_text`: Combined question and answer content, chunked.
- `metadata`: Includes:
  - `data_source`: `"stackoverflow_threads"`,
  - `question_id`: StackOverflow question ID
  - `title`: Question title
  - `tags`: StackOverflow tags
  - `creation_date`: Question creation date
  - `question_score`: Score of the question
  - `answer_score`: Score of the accepted answer
- `code_blocks`: Relevant code blocks extracted from the thread

#### To run:

```bash
python data/chunking/extract_chunk_stack.py
```

### Utility Functions

Several of the chunking scripts rely on shared helper functions to handle common tasks such as code block extraction, chunk-to-code matching, and title parsing. These utilities are defined in:`chatbot-core/data/chunking/utils/`.
