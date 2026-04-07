# Chunking

After collecting and preprocessing the raw content from various sources, the next step in the RAG pipeline is **chunking**. This phase involves splitting the cleaned text into smaller, semantically meaningful units that are suitable for embedding and retrieval by the chatbot.

All chunking scripts are located under the directory:`chatbot-core/data/chunking/`


Below are the chunking procedures for each data source.

---

## Jenkins Documentation

### Script: `extract_chunk_docs.py`

This script performs chunking on the Jenkins documentation using a recursive splitting strategy and enriches the chunks with extracted code blocks and metadata.

- **Input**:  
  `filtered_jenkins_docs.json` — Preprocessed Jenkins documentation (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_docs.json` — Chunked documentation with metadata and code snippets (stored in `chatbot-core/data/processed/`)

### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are approximately **500 characters long** with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splitting is done using a hierarchy of separators: `\n\n`, `\n`, space, and character level.

### Code Block Handling

- Code blocks are extracted from `<pre>` tags using BeautifulSoup.
- The script attempts to reassign these code snippets to the most relevant text chunks using a regex-based system.
- Each chunk includes a list of its associated `code_blocks`.

### Metadata Included in Each Chunk

- `chunk_text`: The chunked text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_documentation"`
  - `source_url`: URL of the original documentation page.
  - `title`: Extracted page title.
- `code_blocks`: Extracted code snippets relevant to this chunk.

### To run:

```bash
python data/chunking/extract_chunk_docs.py
```
> **Note**:
> Ensure `langchain` and the other dependencies in the `requirements.txt` are met in your environment.

## Jenkins Plugin Documentation

### Script: `extract_chunk_plugins.py`

This script processes the pre-cleaned plugin documentation and splits it into consistent text chunks. It also extracts and associates code blocks with the corresponding text segments when available.

- **Input**:  
  `processed_plugin_docs.json` — Cleaned plugin documentation HTML (in `chatbot-core/data/processed/`)

- **Output**:  
  `chunks_plugin_docs.json` — A list of chunked plugin docs with associated metadata (stored in `chatbot-core/data/processed/`)

### Chunking Strategy

- Uses `RecursiveCharacterTextSplitter` from LangChain.
- Chunks are roughly **500 characters** long with **100 characters of overlap**.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Splits text using prioritized separators: paragraph breaks (`\n\n`), single newlines (`\n`), spaces, and individual characters.

### Code Block Handling

- `<pre>` tags are parsed using BeautifulSoup to extract code snippets.
- Extracted blocks are reattached to the most relevant chunk using a positional and regex marker strategy.
- Each chunk includes a `code_blocks` field listing relevant snippets.

### Metadata Included in Each Chunk

- `chunk_text`: The chunked body of text.
- `metadata`: Contains:
  - `data_source`: `"jenkins_plugins_documentation"`
  - `title`: Plugin name as inferred from the source key.
- `code_blocks`: Any code blocks found in the original plugin doc and matched to this chunk.

### To run:

```bash
python data/chunking/extract_chunk_plugins.py
```

## Discourse Topics

### Script: `extract_chunk_discourse.py`

This script processes cleaned Discourse threads by concatenating the posts, extracting code snippets, and splitting the text into semantically coherent chunks. It preserves conversational flow while enriching each chunk with contextual metadata.

- **Input**:  
  `topics_with_posts.json` — A list of Discourse threads with collected question and answer posts (found in `chatbot-core/data/raw/`)

- **Output**:  
  `chunks_discourse_docs.json` — List of processed thread chunks, stored in `chatbot-core/data/processed/`

### Chunking Strategy

- Combines all posts from a thread into a single text block.
- Uses `RecursiveCharacterTextSplitter` from LangChain to split the content into chunks of roughly **500 characters** with **100 characters overlap**.
- Text is chunked using prioritized separators: double newline, single newline, space, and then character-level.

### Code Block Handling

- The script identifies both:
  - **Multiline code blocks** 
  - **Inline code snippets**
- Code blocks are identified using regex patterns.
- Code blocks are replaced with placeholder tokens before chunking.
- Code blocks are listed under the `code_blocks` field in each chunk.

### Metadata Included in Each Chunk

- `chunk_text`: The text content of the chunk.
- `metadata`: Includes:
  - `data_source`: `"discourse_threads"`
  - `topic_id`: Discourse topic ID
  - `title`: Title of the thread
- `code_blocks`: Extracted code snippets from the thread text, if any.

### To run:

```bash
python data/chunking/extract_chunk_discourse.py
```

## StackOverflow Threads

### Script: `extract_chunk_stack.py`

This script takes the filtered StackOverflow data, parses the HTML from both questions and answers, extracts code snippets, and chunks the content into structured units.

- **Input**:  
  `stack_overflow_threads.json` — Contains structured Q&A pairs with metadata, located in `chatbot-core/data/raw/`

- **Output**:  
  `chunks_stackoverflow_threads.json` — A list of chunked question-answer pairs, saved in `chatbot-core/data/processed/`

### Chunking Strategy

- Questions and accepted answers are concatenated into a single text block.
- HTML is parsed with BeautifulSoup, and the text is extracted using `get_text()`, with separator as `\n`.
- Uses `RecursiveCharacterTextSplitter` from LangChain to generate chunks:
  - **500 characters per chunk**
  - **100 character overlap**
  - Splitting hierarchy: paragraph (`\n\n`), newline (`\n`), space, and character.

### Code Block Handling

- Extracts `<code>` blocks from the HTML content.
- Code blocks are temporarily replaced with placeholders (the format is defined by `PLACEHOLDER_TEMPLATE`; e.g `[[CODE_BLOCK_n]]`) before chunking.
- Post-chunking, the placeholders are matched back to their original code snippets and added under `code_blocks`.

### Metadata Included in Each Chunk

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

### To run:

```bash
python data/chunking/extract_chunk_stack.py
```

## Utility Functions

Several of the chunking scripts rely on shared helper functions to handle common tasks such as code block extraction, chunk-to-code matching, and title parsing. These utilities are defined in:`chatbot-core/data/chunking/utils/`.
