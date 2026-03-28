# LLM-as-a-Judge Evaluation Framework

An automated evaluation pipeline for assessing the Jenkins AI Chatbot's response quality.

## Overview

This framework sends a set of predefined Jenkins-related questions to the chatbot API and scores the responses on three dimensions:

- **Faithfulness**: Is the response grounded in accurate Jenkins documentation?
- **Relevance**: Does the response directly address the question asked?
- **Completeness**: Does the response cover the key topics a user would need?

## Scoring Methods

### Topic Coverage (always available)
Checks whether the expected topic keywords appear in the chatbot's response. This works without any external dependencies and provides a baseline quality signal.

### LLM-as-a-Judge (optional, requires Groq API key)
Uses a secondary LLM (Llama 3 70B via Groq) to evaluate each response on a 1-5 scale across all three dimensions, with reasoning for each score. This provides more nuanced evaluation but requires a free [Groq API key](https://console.groq.com).

## Usage

### Basic (topic coverage only)
```bash
cd chatbot-core
export PYTHONPATH=$(pwd)
python -m evaluation.evaluate
```

### With LLM Judge
```bash
export GROQ_API_KEY=your_key_here
python -m evaluation.evaluate
```

### Custom API URL
```bash
python -m evaluation.evaluate --api-url http://localhost:8001
```

### Custom output path
```bash
python -m evaluation.evaluate --output results/my_eval.json
```

## Test Questions

The test question set (`test_questions.json`) covers five categories:

| Category | Description | Count |
|----------|-------------|-------|
| Documentation | General Jenkins usage and setup | 5 |
| Plugin | Plugin-specific questions | 3 |
| Troubleshooting | Common error scenarios | 3 |
| Configuration | Jenkins administration tasks | 3 |
| Advanced | Complex pipeline topics | 1 |

Each question includes expected topic keywords and a difficulty rating (easy/medium/hard).

To add new test questions, edit `test_questions.json` following the existing format.

## Output

The evaluation produces a JSON report with:

- **metadata**: Timestamp, API URL, configuration
- **summary**: Aggregate scores and statistics
- **results**: Per-question scores, response excerpts, and latency

## Adding to Makefile

To run the evaluation with a single command, add this target to the project Makefile:

```makefile
run-evaluation: setup-backend
	@$(BACKEND_SHELL) && python -m evaluation.evaluate
```
