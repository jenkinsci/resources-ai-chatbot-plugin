# Quick Start: Build Failure Analysis

## 🚀 What This Does

Analyzes Jenkins build failures automatically - fetches logs, removes sensitive data, identifies errors, and suggests fixes.

## ⚡ Quick Test

```bash
cd chatbot-core
python validate_build_analyzer.py
```

Expected output: ✅ ALL TESTS PASSED

## 🔧 Setup (2 minutes)

### 1. Configure Jenkins (choose one):

**Environment Variables:**
```bash
export JENKINS_URL=http://jenkins:8080
export JENKINS_USERNAME=your_username
export JENKINS_API_TOKEN=your_token
```

**Or edit `chatbot-core/api/config/config.yml`:**
```yaml
jenkins:
  url: "http://jenkins:8080"
  username: "your_username"
  api_token: "your_token"
```

### 2. Start Server:
```bash
cd chatbot-core
uvicorn api.main:app --reload
```

### 3. Test API:
```bash
curl -X POST http://localhost:8000/api/chatbot/build-analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"job_name": "test-job", "build_number": 1}'
```

## 📊 What You Get

```json
{
  "error_type": "null_pointer_exception",
  "error_message": "java.lang.NullPointerException",
  "sanitized_log": "ERROR at line 42...",
  "similar_issues": [...],
  "suggested_fix": "## Fix:\n1. Add null check\n2. ..."
}
```

## 🔒 Security

✅ All passwords, API keys, tokens automatically redacted
✅ 100% test coverage for PII sanitization
✅ Run tests: `python validate_build_analyzer.py`

## 📚 Full Docs

- Feature Guide: `docs/chatbot-core/build-failure-analysis.md`
- PR Details: `docs/PR_BUILD_FAILURE_ANALYSIS.md`
- Code: `chatbot-core/api/services/tools/build_failure_analyzer.py`

## ❓ Issues?

1. **Can't connect to Jenkins**: Check URL and API token
2. **PII not redacted**: Run validation script
3. **No similar issues found**: FAISS vector DB needs to be populated

## 💰 Cost

**FREE** - No LLM calls required for base functionality!
