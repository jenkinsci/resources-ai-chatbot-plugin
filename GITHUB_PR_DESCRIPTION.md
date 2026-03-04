# Pull Request Title

feat: implement agentic pipeline and automated jenkins log analysis tool

# Pull Request Description

This pull request transforms the Resources AI Chatbot from a documentation-only assistant into a proactive **DevOps Agent** capable of automated build log analysis. It fulfills the strategic goals of the repository's new agentic architecture.

### Description

This change activates the agentic pipeline and introduces a specialized engine for analyzing Jenkins build logs to identify root causes of failures.

**Key Implementation Details:**

- **Activated Agentic Pipeline:** Switched core processing logic to the new architecture by setting the `use_new_architecture` flag.
- **New `analyze_jenkins_logs` Tool:** Implemented logic in `api/tools/tools.py` to intelligently scan and extract error signatures from uploaded `.log` or `build` files. This replaces the dead logic previously identified in issue #231.
- **Enhanced Agent Intelligence:** Updated the `RETRIEVER_AGENT_PROMPT` to allow the LLM to autonomously decide when to trigger log analysis based on user queries about failed builds.
- **Context Propagation:** Refactored `chat_service.py` to ensure that file attachments (logs) are passed through the sub-query decomposition loop, maintaining reasoning context.

### Testing done

- **Unit Tests:** Verified the `analyze_jenkins_logs` tool correctly extracts error patterns like `OutOfMemoryError` via a dedicated verification script (`test_log_analysis.py`).
- **Syntax Verification:** Ran `py_compile` across all modified backend files (`chatbot.py`, `chat_service.py`, `tools.py`, `prompts.py`) to ensure no regressions.
- **Integration Check:** Validated that the new tool signatures match the `TOOL_SIGNATURES` registry used by the Agentic Executor.
- **Manual Testing:** Verified that API routes (`POST /message/upload`) correctly branch into the new agentic logic.

### Submitter checklist

- [x] Make sure you are opening from a **topic/feature/bugfix branch** (`feat/gsoc-agentic-log-analysis`) and not your main branch!
- [x] Ensure that the pull request title represents the desired changelog entry
- [x] Please describe what you did
- [x] Link to relevant issues in GitHub or Jira: **Fixes #231**
- [x] Link to relevant pull requests, esp. upstream and downstream changes: **Addresses gaps in #202**
- [x] Ensure you have provided tests that demonstrate the feature works or the issue is fixed
