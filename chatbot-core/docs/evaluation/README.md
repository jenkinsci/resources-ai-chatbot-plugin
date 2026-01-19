# LLM-as-a-Judge Evaluation Pipeline

## Overview

This evaluation pipeline implements automated quality assessment for the Jenkins AI Chatbot using the "LLM-as-a-Judge" approach. It helps ensure that changes to prompt engineering or retrieval logic don't degrade chatbot performance.

## Architecture

```
┌─────────────────────┐
│  Golden Dataset     │
│  (Q&A Pairs)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Chatbot System     │
│  (Generate Answers) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ragas Framework    │
│  (Compute Metrics)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Evaluation Report  │
│  (Pass/Fail)        │
└─────────────────────┘
```

## Metrics

### 1. Faithfulness (Threshold: ≥ 0.85)
**What it measures:** Does the chatbot avoid hallucinations?

**How it works:** Compares the generated answer against the retrieved context to ensure all claims are supported by the source documents.

**Why it matters:** Prevents the chatbot from making up information not present in the documentation.

### 2. Answer Relevancy (Threshold: ≥ 0.75)
**What it measures:** Does the answer actually address the question?

**How it works:** Evaluates how well the generated answer relates to the original question.

**Why it matters:** Ensures the chatbot stays on topic and doesn't provide tangential information.

### 3. Context Recall (Threshold: ≥ 0.80)
**What it measures:** Did the retrieval system find the right documents?

**How it works:** Checks if the retrieved context contains the information needed to answer the question (compared to ground truth).

**Why it matters:** Tests the effectiveness of the RAG retrieval pipeline.

### 4. Context Precision (Threshold: ≥ 0.75)
**What it measures:** Are the retrieved documents relevant?

**How it works:** Evaluates whether the retrieved context is actually useful for answering the question.

**Why it matters:** Reduces noise in the context and improves answer quality.

## Golden Dataset

The golden dataset is located at `chatbot-core/data/evaluation/golden_dataset.json` and contains verified Q&A pairs covering:

- **Jenkins Core:** Installation, configuration, basic concepts
- **Plugins:** Installation, updates, popular plugins
- **Error Scenarios:** Common errors and troubleshooting

### Dataset Structure

```json
{
  "id": "unique_identifier",
  "category": "Jenkins Core | Plugins | Error Scenarios",
  "question": "User question",
  "ground_truth_answer": "Verified correct answer",
  "expected_context_keywords": ["keyword1", "keyword2"]
}
```

### Adding New Test Cases

1. Edit `chatbot-core/data/evaluation/golden_dataset.json`
2. Add a new entry with all required fields
3. Ensure the answer is accurate and comprehensive
4. Run validation: `pytest tests/evaluation/test_llm_evaluation.py::test_golden_dataset_structure -v`

## Running Evaluations

### Quick Start (Recommended)

Use the provided helper scripts that automatically activate the virtual environment:

```bash
# Linux/Mac
cd chatbot-core
./run_evaluation_tests.sh

# Windows
cd chatbot-core
.\run_evaluation_tests.bat
```

### Local Testing (Dataset Validation Only)

```bash
cd chatbot-core
pytest tests/evaluation/ -v
```

This runs:
- Dataset structure validation
- Category coverage checks

### Full Evaluation (Requires LLM API)

```bash
cd chatbot-core
RUN_EVALUATION=true pytest tests/evaluation/test_llm_evaluation.py::test_chatbot_evaluation_metrics -v
```

**Requirements:**
- OpenAI API key (or compatible LLM endpoint)
- Set `OPENAI_API_KEY` environment variable

### CI/CD Integration

The evaluation pipeline runs automatically in GitHub Actions:

#### Automatic Triggers
- **Dataset Validation:** Runs on every PR
- **Full Evaluation:** Runs when PR has `evaluate` label

#### Manual Trigger
1. Go to Actions tab in GitHub
2. Select "LLM-as-a-Judge Evaluation" workflow
3. Click "Run workflow"
4. Choose whether to run full evaluation

## Interpreting Results

### Example Output

```
EVALUATION RESULTS
================================================================================
faithfulness        : 0.8923
answer_relevancy    : 0.8156
context_recall      : 0.8445
context_precision   : 0.7891
================================================================================
✅ All metrics passed the threshold!
```

### What to Do If Tests Fail

#### Faithfulness < 0.85
**Problem:** Chatbot is hallucinating or adding unsupported information

**Solutions:**
- Review prompt engineering to emphasize staying grounded in context
- Check if LLM temperature is too high
- Verify retrieval is returning relevant documents

#### Answer Relevancy < 0.75
**Problem:** Answers are off-topic or don't address the question

**Solutions:**
- Improve prompt to focus on answering the specific question
- Check if context is too noisy
- Review question understanding in the prompt

#### Context Recall < 0.80
**Problem:** Retrieval system isn't finding the right documents

**Solutions:**
- Improve chunking strategy
- Adjust embedding model or similarity threshold
- Expand the knowledge base

#### Context Precision < 0.75
**Problem:** Retrieved documents contain too much irrelevant information

**Solutions:**
- Tune retrieval parameters (top-k, similarity threshold)
- Improve document preprocessing
- Consider hybrid search (semantic + keyword)

## Cost Management

Full evaluations use an LLM API (OpenAI by default) which incurs costs:

- **Estimated cost per run:** ~$0.10-0.50 (depends on dataset size and model)
- **Recommendation:** Run full evaluation only on PRs that change:
  - Prompt engineering
  - Retrieval logic
  - RAG pipeline
  - LLM configuration

## Extending the Pipeline

### Adding New Metrics

1. Import metric from Ragas:
   ```python
   from ragas.metrics import your_new_metric
   ```

2. Add to evaluation in `test_llm_evaluation.py`:
   ```python
   result = evaluate(
       eval_dataset,
       metrics=[faithfulness, answer_relevancy, your_new_metric]
   )
   ```

3. Update thresholds and documentation

### Using a Different LLM for Evaluation

By default, Ragas uses OpenAI. To use a different LLM:

```python
from langchain_community.llms import YourLLM

# Configure in test file
eval_llm = YourLLM(...)
result = evaluate(eval_dataset, metrics=[...], llm=eval_llm)
```

### Expanding the Dataset

Target: 100+ Q&A pairs (currently 10)

**Priority areas:**
- Advanced pipeline configurations
- Security and permissions
- Distributed builds
- Plugin conflicts
- Performance troubleshooting

## Files Structure

```
chatbot-core/
├── data/
│   └── evaluation/
│       ├── golden_dataset.json          # Q&A pairs
│       └── results/
│           └── latest_evaluation.json   # Latest scores
├── tests/
│   └── evaluation/
│       ├── __init__.py
│       └── test_llm_evaluation.py       # Main test suite
├── docs/
│   └── evaluation/
│       └── README.md                    # This file
└── pytest.ini                           # Pytest configuration

.github/
└── workflows/
    └── llm-evaluation.yml               # CI/CD workflow
```

## Troubleshooting

### "Golden dataset not found"
- Ensure `chatbot-core/data/evaluation/golden_dataset.json` exists
- Check file path in test fixtures

### "Evaluation failed (likely missing LLM API key)"
- Set `OPENAI_API_KEY` environment variable
- Or configure alternative LLM provider

### "Module 'ragas' not found"
- Install dependencies: `pip install -r requirements.txt`
- Ensure ragas and datasets packages are installed

## References

- [Ragas Documentation](https://docs.ragas.io/)
- [LLM-as-a-Judge Paper](https://arxiv.org/abs/2306.05685)
- [Issue #70](https://github.com/jenkinsci/resources-ai-chatbot-plugin/issues/70)
