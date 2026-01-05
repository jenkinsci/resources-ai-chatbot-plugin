# Build Failure Analysis Feature

## Overview

This feature extends the Jenkins chatbot from a "Knowledge Assistant" to an **Operational Co-pilot** that can proactively analyze build failures, sanitize sensitive data, and provide actionable insights.

## Architecture

```
User Request → FastAPI Endpoint → BuildFailureAnalyzer Tool
                                          ↓
                      1. Fetch console log from Jenkins
                                          ↓
                      2. Extract error context (LogExtractor)
                                          ↓
                      3. Sanitize PII (LogSanitizer) ⚠️ CRITICAL
                                          ↓
                      4. Classify error type
                                          ↓
                      5. Search FAISS vector DB for similar issues
                                          ↓
                      6. Generate suggestions based on error type
                                          ↓
                      Return structured analysis to user
```

## Components

### 1. LogSanitizer
- **Location**: `api/services/tools/build_failure_analyzer.py`
- **Purpose**: Remove PII and sensitive information from logs
- **Redacts**:
  - API keys
  - Passwords
  - Auth tokens (JWT, Bearer, etc.)
  - AWS credentials
  - Private SSH keys
  - Email addresses
  - IP addresses
  - URLs with embedded credentials

### 2. LogExtractor
- **Location**: `api/services/tools/build_failure_analyzer.py`
- **Purpose**: Extract relevant error context from large console logs
- **Features**:
  - Identifies error markers (ERROR, FATAL, Exception, etc.)
  - Extracts context lines around errors
  - Cleans error messages for vector search
  - Limits output to configurable line count

### 3. BuildFailureAnalyzer (LangChain Tool)
- **Location**: `api/services/tools/build_failure_analyzer.py`
- **Purpose**: Main tool that orchestrates build failure analysis
- **Capabilities**:
  - Connects to Jenkins REST API
  - Fetches console logs
  - Sanitizes and extracts errors
  - Searches FAISS vector database for similar issues
  - Classifies error types
  - Returns structured analysis data

### 4. FastAPI Endpoint
- **Location**: `api/routes/build_analysis.py`
- **Endpoint**: `POST /api/chatbot/build-analysis/analyze`
- **Purpose**: HTTP interface for build failure analysis
- **Returns**: Structured response with error analysis and suggestions

## API Usage

### Request

```http
POST /api/chatbot/build-analysis/analyze
Content-Type: application/json

{
  "job_name": "my-jenkins-job",
  "build_number": 123,
  "jenkins_url": "https://jenkins.example.com",
  "username": "jenkins_user",
  "api_token": "jenkins_api_token"
}
```

**Note**: `jenkins_url`, `username`, and `api_token` are optional if configured in `config.yml`.

**Security**: The API validates Jenkins URLs to prevent SSRF attacks. Private IPs and internal endpoints are blocked. Use the configured Jenkins instance or explicitly allowlist external Jenkins servers.

### Response

```json
{
  "status": "success",
  "job_name": "my-jenkins-job",
  "build_number": 123,
  "error_type": "null_pointer_exception",
  "error_message": "java.lang.NullPointerException: Cannot invoke method",
  "log_summary": "java.lang.NullPointerException...",
  "sanitized_log": "Line 45: ERROR...\n[REDACTED_PASSWORD]...",
  "similar_issues": [
    {
      "source": "stackoverflow",
      "title": "How to fix NullPointerException",
      "url": "https://stackoverflow.com/...",
      "excerpt": "This error occurs when...",
      "relevance_score": 0.85
    }
  ],
  "redacted_fields": ["password", "api_key"],
  "total_similar_issues": 3,
  "suggested_fix": "## NullPointerException Detected\n\n**Common Causes:**..."
}
```

## Configuration

Add to `.env` file (optional - overrides config.yml):

```bash
JENKINS_URL=https://your-jenkins-url:8443
JENKINS_USERNAME=your_username
JENKINS_API_TOKEN=your_api_token
```

**⚠️ Security Note**: Always use HTTPS for Jenkins connections to protect credentials and log data in transit.

Or update `api/config/config.yml`:

```yaml
jenkins:
  url: "https://localhost:8443"
  username: "admin"
  api_token: "your_token_here"

build_analysis:
  max_log_size_bytes: 5242880  # 5MB
  context_lines: 50
  enable_pii_detection: true
  timeout_seconds: 30
  max_similar_issues: 5
```

## Security Features

### ⚠️ CRITICAL: PII Sanitization

All logs are automatically sanitized before being processed or sent to any LLM. The `LogSanitizer` class:

1. **Scans for sensitive patterns** using regex
2. **Replaces matches** with `[REDACTED_TYPE]` markers
3. **Logs redaction events** for audit purposes
4. **Returns list of redacted types** in response

### Unit Tests

Comprehensive security tests in `tests/unit/test_log_sanitizer.py`:

```bash
# Run security tests
cd chatbot-core
pytest tests/unit/test_log_sanitizer.py -v
```

All tests must pass before deployment!

## Error Classification

The system automatically classifies errors into these types:

| Error Type | Keywords | Common Causes |
|------------|----------|---------------|
| `compilation_error` | javac, compilation failed | Syntax errors, missing imports |
| `test_failure` | test failed, junit, assertion | Test assertion mismatches |
| `dependency_error` | could not resolve, artifact not found | Maven/Gradle dependency issues |
| `null_pointer_exception` | NullPointerException | Accessing null objects |
| `out_of_memory` | OutOfMemoryError, heap space | Insufficient memory |
| `network_error` | connection refused, unknown host | Network connectivity |
| `permission_error` | permission denied, unauthorized | File/resource permissions |
| `timeout_error` | timeout, timed out | Operation exceeded time limit |
| `configuration_error` | no such file, invalid configuration | Missing/invalid config |
| `unknown_error` | Other | Unclassified errors |

## Integration with Agent Architecture

The `BuildFailureAnalyzer` is a LangChain `BaseTool` that can be added to the agent's tool registry:

```python
from api.services.tools.build_failure_analyzer import BuildFailureAnalyzer

# Initialize with vector store for similarity search
analyzer = BuildFailureAnalyzer(
    jenkins_url=config['jenkins']['url'],
    username=config['jenkins']['username'],
    api_token=config['jenkins']['api_token'],
    vector_store=faiss_vector_store  # Optional
)

# Add to agent's tools
agent_tools.append(analyzer)
```

The agent can then use this tool when analyzing build failures.

## Cost Analysis

### Free Components (100% Free)
- Jenkins API calls
- PII sanitization (regex-based)
- Error extraction and classification
- Local log processing

### Optional LLM Costs
- **Without LLM**: $0 (pure rule-based analysis)
- **With LLM** (for enhanced insights): ~$0.003 per analysis
- **Hybrid approach** (70% cached): ~$0.001 per analysis average

The system is designed to work WITHOUT requiring LLM calls. LLM is only used by the agent if it needs to provide enhanced explanations.

## Future Enhancements

1. **Real-time monitoring**: WebSocket support for live build analysis
2. **Historical analysis**: Track recurring errors across builds
3. **Auto-fix suggestions**: Generate code patches for common errors
4. **Jenkins plugin integration**: Native Jenkins UI integration
5. **Multi-project analysis**: Compare errors across multiple jobs
6. **ML-based classification**: Improve error classification with ML models

## Testing

### Run All Tests

```bash
cd chatbot-core
pytest tests/unit/test_log_sanitizer.py -v
```

### Test Coverage

- ✅ API key redaction
- ✅ Password redaction
- ✅ JWT token redaction
- ✅ Email redaction
- ✅ Private key redaction
- ✅ AWS credentials redaction
- ✅ IP address redaction
- ✅ URL credentials redaction
- ✅ Multiple PII types
- ✅ Case-insensitive matching
- ✅ Error context extraction
- ✅ Error classification
- ✅ Vector store integration

## Troubleshooting

### Jenkins Connection Issues

```bash
# Test Jenkins API connection
curl -u username:api_token http://jenkins-url/job/job-name/123/consoleText
```

### PII Not Being Redacted

Check logs for redaction events:
```
INFO: Redacted 3 instances of password
INFO: Redacted 1 instances of api_key
```

### No Similar Issues Found

- Ensure FAISS vector database is populated
- Check that embeddings include StackOverflow/Discourse content
- Verify error message cleaning is working correctly

## Support

For issues or questions:
1. Check logs in `chatbot-core/logs/`
2. Run unit tests to verify installation
3. Review Jenkins API permissions
4. Check FAISS vector database status
