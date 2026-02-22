# LLM-as-a-Judge Evaluation

This document describes the automated evaluation pipeline added for issue #70.

## Goals

The pipeline adds regression checks for chatbot quality when prompt/retrieval logic changes.
It evaluates three metrics:

- `faithfulness`: whether the answer is supported by retrieved context.
- `context_recall`: whether retrieved context contains the information needed to answer.
- `answer_relevance`: whether the answer actually addresses the question.

## Dataset

The golden dataset lives in:

- `chatbot-core/evaluation/dataset/golden_qa_dataset.jsonl`
- `chatbot-core/evaluation/dataset/golden_qa_dataset.csv`

It currently contains 106 curated Q/A samples across:

- Jenkins core concepts
- plugin usage/setup
- troubleshooting and error scenarios

Each row contains:

- `id`
- `category`
- `question`
- `ground_truth`
- `reference_context`

Regenerate both dataset formats:

```bash
make generate-eval-dataset
```

or:

```bash
cd chatbot-core
python evaluation/build_golden_dataset.py
```

## Local Execution

The evaluation suite is opt-in because it makes external LLM calls.

Required environment variables:

- `JUDGE_LLM_API_BASE_URL`
- `JUDGE_LLM_MODEL`

Optional:

- `JUDGE_LLM_API_KEY`
- `CANDIDATE_LLM_API_BASE_URL` (defaults to judge endpoint)
- `CANDIDATE_LLM_MODEL` (defaults to judge model)
- `CANDIDATE_LLM_API_KEY` (defaults to judge key)

Common controls:

- `LLM_EVAL_SAMPLE_SIZE` (default `30`, set `0` for full dataset)
- `LLM_EVAL_FAITHFULNESS_THRESHOLD` (default `0.85`)
- `LLM_EVAL_CONTEXT_RECALL_THRESHOLD` (default `0.85`)
- `LLM_EVAL_ANSWER_RELEVANCE_THRESHOLD` (default `0.85`)
- `LLM_EVAL_REPORT_PATH` (default `evaluation/report/llm_judge_report.json`)
- `LLM_EVAL_STORE_SAMPLE_DETAILS` (default `0`, redacts sample text fields)
- `LLM_EVAL_MAX_STORED_TEXT_CHARS` (default `1200`, used only when details are enabled)

Run with pytest:

```bash
make run-llm-eval
```

Run with CLI script:

```bash
cd chatbot-core
python evaluation/run_llm_judge_eval.py --enforce-thresholds
```

## Report Interpretation

The JSON report stores:

- aggregate metric means
- threshold configuration used
- per-sample answers, retrieved context, and judge reasons

Interpretation guidance:

- `>= 0.90`: strong quality
- `0.85 - 0.89`: acceptable, inspect recent changes
- `< 0.85`: likely regression, investigate failing samples before merge

Focus first on per-sample judge reasons in low-scoring rows to identify:

- unsupported claims (faithfulness)
- missing retrieval coverage (context recall)
- answers that are off-topic (answer relevance)

## Data Leakage Controls

The evaluator is configured to reduce leakage risk by default:

- sample text fields (`question`, `candidate_answer`, `retrieved_context`) are redacted in output reports unless `LLM_EVAL_STORE_SAMPLE_DETAILS=1`
- API keys are never serialized into report artifacts
- CI workflow runs keep redaction enabled

Enable detailed sample storage only in trusted/internal environments where generated outputs are approved for persistence.

## CI Integration

Workflow file:

- `.github/workflows/llm-judge-eval.yml`

Trigger behavior:

- manual `workflow_dispatch`, or
- PR event when label `run-llm-eval` is present

To control cost, the workflow is intentionally separated from normal unit/integration CI.
By default it evaluates 30 samples; use manual dispatch with a larger `sample_size` for deeper checks.
