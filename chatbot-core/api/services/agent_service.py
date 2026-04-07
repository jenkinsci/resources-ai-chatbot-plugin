"""
Agent Service implementing the core agents of the Agentic Architecture.
"""
import logging
from typing import Optional

from api.services.jenkins_service import jenkins_client
from api.prompts.prompts import LOG_ANALYSIS_INSTRUCTION
from api.models.llama_cpp_provider import llm_provider
from api.prompts.prompt_builder import _build_system_message, _build_user_message

logger = logging.getLogger(__name__)

class DocumentingAgent:
    """Agent 2: Retrieves Jenkins documentation context."""
    
    @staticmethod
    def get_docs(user_input: str) -> str:
        # Import dynamically to avoid circular dependencies
        from api.services.chat_service import retrieve_context
        logger.info("[Agent 2] Documenting Agent is retrieving docs for query.")
        return retrieve_context(user_input)

class LogAnalyzingAgent:
    """Agent 3: Analyzes runtime logs from Jenkins API."""
    
    @staticmethod
    def analyze_logs(user_input: str) -> Optional[str]:
        # For simplicity, if the query relates to "fail", "error", "log", "why", 
        # we trigger the runtime log analysis.
        triggers = ["fail", "error", "log", "why", "issue", "break", "broke"]
        if not any(t in user_input.lower() for t in triggers):
            logger.info("[Agent 3] No log analysis required based on query.")
            return None
            
        logger.info("[Agent 3] Log Analyzing Agent is retrieving runtime data from Jenkins API.")
        logs = jenkins_client.get_recent_failed_build_logs()
        
        if not logs or "No recent logs" in logs:
             return None
        
        logger.info("[Agent 3] Analyzing logs with LLM.")
        
        # Build prompt for log analysis
        prompt = f"System:\n{LOG_ANALYSIS_INSTRUCTION}\n\nUser-Provided Log Data:\n{logs}\n\nUser Question:\n{user_input}\n\nAssistant:"
        
        from api.services.chat_service import generate_answer
        analysis = generate_answer(prompt, max_tokens=256)
        
        return analysis

class AgentOrchestrator:
    """Agent 1: Coordinates docs retrieval and log analysis."""
    
    @staticmethod
    def synthesize_context(user_input: str) -> str:
        logger.info("[Agent 1] Orchestrator is coordinating Agents.")
        
        # Agent 2 call
        docs_context = DocumentingAgent.get_docs(user_input)
        
        # Agent 3 call
        log_analysis = LogAnalyzingAgent.analyze_logs(user_input)
        
        # Combine
        combined_context = "[Documentation Context]\n" + docs_context
        
        if log_analysis:
            combined_context += "\n\n[Runtime Log Analysis (Agent 3)]\n" + log_analysis
            logger.info("[Agent 1] Successfully combined Documentation and Runtime Log Analysis.")
        else:
            logger.info("[Agent 1] Using only Documentation Context.")
            
        return combined_context

# Singleton instances for easy import
documenting_agent = DocumentingAgent()
log_analyzing_agent = LogAnalyzingAgent()
agent_orchestrator = AgentOrchestrator()
