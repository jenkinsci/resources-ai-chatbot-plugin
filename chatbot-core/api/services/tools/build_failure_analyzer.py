"""
Build Failure Analysis Tool for Jenkins
Fetches, sanitizes, and analyzes build logs to provide actionable insights.
Works with the agent's vector database to find similar issues.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from langchain.tools import BaseTool
from pydantic import Field
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class LogSanitizer:
    """Sanitizes logs to remove PII and sensitive information"""
    
    # Patterns for common sensitive data
    # Order matters - more specific patterns should be checked first
    PATTERNS = [
        ('url_with_credentials', r'https?://[^:]+:[^@]+@[^\s]+'),
        ('private_key', r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (RSA |DSA |EC )?PRIVATE KEY-----'),
        ('jwt_token', r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'),
        ('aws_key', r'(?i)(aws_access_key_id|aws_secret_access_key)[\s:=]+["\']?([A-Za-z0-9/+=]{20,})["\']?'),
        ('api_key', r'(?i)(api[_-]?key|apikey)[\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
        ('password', r'(?i)(password|passwd|pwd)[\s:=]+["\']?([^\s"\']{8,})["\']?'),
        ('token', r'(?i)(token|auth|bearer)[\s:=]+["\']?([a-zA-Z0-9_\-\.]{20,})["\']?'),
        ('email', r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        ('ip_address', r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
    ]
    
    @classmethod
    def sanitize(cls, log_content: str) -> Tuple[str, List[str]]:
        """
        Sanitize log content by masking sensitive information
        
        Args:
            log_content: Raw log content
            
        Returns:
            Tuple of (sanitized_content, list_of_redacted_types)
        """
        sanitized = log_content
        redacted_types = []
        
        for pattern_name, pattern in cls.PATTERNS:
            matches = re.findall(pattern, sanitized)
            if matches:
                redacted_types.append(pattern_name)
                sanitized = re.sub(pattern, f'[REDACTED_{pattern_name.upper()}]', sanitized)
                logger.info(f"Redacted {len(matches)} instances of {pattern_name}")
        
        return sanitized, list(set(redacted_types))


class LogExtractor:
    """Extracts relevant error information from console logs"""
    
    ERROR_MARKERS = [
        'ERROR', 'FATAL', 'FAILED', 'Exception', 'Error:', 
        'BUILD FAILED', 'FAILURE', 'java.lang.', 'Caused by:',
        'at com.', 'at org.', 'at io.', 'at net.'
    ]
    
    @classmethod
    def extract_error_context(cls, log_content: str, context_lines: int = 50) -> str:
        """
        Extract relevant error context from full log
        
        Args:
            log_content: Full console log
            context_lines: Maximum number of lines to extract
            
        Returns:
            Condensed log with error context
        """
        lines = log_content.split('\n')
        
        # Find lines with error markers
        error_indices = []
        for i, line in enumerate(lines):
            if any(marker in line for marker in cls.ERROR_MARKERS):
                error_indices.append(i)
        
        if not error_indices:
            # No explicit errors found, return last N lines
            return '\n'.join(lines[-context_lines:])
        
        # Extract context around each error
        extracted_lines = set()
        for idx in error_indices:
            start = max(0, idx - 5)  # 5 lines before
            end = min(len(lines), idx + 20)  # 20 lines after
            extracted_lines.update(range(start, end))
        
        # Sort and get unique lines
        sorted_indices = sorted(extracted_lines)
        
        # Limit total lines
        if len(sorted_indices) > context_lines:
            # Keep first errors and last errors
            sorted_indices = sorted_indices[:context_lines//2] + sorted_indices[-context_lines//2:]
        
        # Build condensed log with line numbers
        result = []
        prev_idx = -2
        for idx in sorted(sorted_indices):
            if idx - prev_idx > 1:
                result.append('[... log lines omitted ...]')
            result.append(f"Line {idx}: {lines[idx]}")
            prev_idx = idx
        
        return '\n'.join(result)
    
    @classmethod
    def extract_key_error(cls, log_content: str) -> str:
        """
        Extract the main error message for vector search
        
        Args:
            log_content: Sanitized log content
            
        Returns:
            Key error message cleaned for search
        """
        lines = log_content.split('\n')
        
        # Look for exception class names or ERROR markers
        for line in lines:
            if 'Exception' in line or 'Error' in line or 'FATAL' in line:
                # Clean up line numbers and paths for better matching
                clean_line = re.sub(r':\d+', '', line)  # Remove line numbers
                clean_line = re.sub(r'Line \d+:', '', clean_line)  # Remove our line markers
                clean_line = re.sub(r'/[^\s]+/', '', clean_line)  # Remove paths
                clean_line = re.sub(r'\\[^\s]+\\', '', clean_line)  # Remove Windows paths
                clean_line = re.sub(r'\([^)]+\.java:\d+\)', '', clean_line)  # Remove (File.java:123)
                return clean_line.strip()
        
        return "Unknown build error"


class BuildFailureAnalyzer(BaseTool):
    """
    Tool for analyzing Jenkins build failures
    Does NOT directly call LLM - returns structured data for the agent
    """
    
    name: str = "build_failure_analyzer"
    description: str = """
    Analyzes Jenkins build failures by:
    1. Fetching console logs from Jenkins
    2. Sanitizing sensitive data (PII, passwords, API keys)
    3. Extracting the specific error message/stack trace
    4. Searching the vector database for similar issues
    
    Returns structured error information with similar issues from the knowledge base.
    
    Input should be a JSON string with keys:
    - job_name: Name of the Jenkins job (required)
    - build_number: Build number to analyze (required)
    - jenkins_url: Base Jenkins URL (optional, uses config default)
    - username: Jenkins username (optional, uses config default)
    - api_token: Jenkins API token (optional, uses config default)
    """
    
    jenkins_url: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)
    api_token: Optional[str] = Field(default=None)
    vector_store: Any = Field(default=None)
    
    def _run(self, query: str) -> str:
        """Execute the build failure analysis"""
        try:
            import json
            params = json.loads(query)
            
            jenkins_url = params.get('jenkins_url', self.jenkins_url)
            job_name = params['job_name']
            build_number = params['build_number']
            username = params.get('username', self.username)
            api_token = params.get('api_token', self.api_token)
            
            # 1. Fetch console log
            logger.info(f"Fetching console log for {job_name} #{build_number}")
            console_log = self._fetch_console_log(
                jenkins_url, job_name, build_number, username, api_token
            )
            
            # 2. Extract error context (reduce size)
            error_context = LogExtractor.extract_error_context(console_log)
            
            # 3. Sanitize PII
            sanitized_log, redacted_types = LogSanitizer.sanitize(error_context)
            
            # 4. Classify error type
            error_type = self._classify_error(sanitized_log)
            
            # 5. Extract key error message for vector search
            error_message = LogExtractor.extract_key_error(sanitized_log)
            
            # 6. Search FAISS for similar issues
            similar_issues = self._search_similar_issues(error_message)
            
            # Return structured data - Agent decides what to do next
            analysis = {
                'status': 'success',
                'job_name': job_name,
                'build_number': build_number,
                'error_type': error_type,
                'error_message': error_message,
                'sanitized_log': sanitized_log[:2000],  # First 2000 chars for context
                'similar_issues': similar_issues,
                'redacted_fields': redacted_types,
                'total_similar_issues': len(similar_issues)
            }
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            logger.error(f"Build failure analysis error: {str(e)}", exc_info=True)
            return json.dumps({
                'status': 'error',
                'message': f"Failed to analyze build: {str(e)}"
            })
    
    def _fetch_console_log(
        self, 
        jenkins_url: str, 
        job_name: str, 
        build_number: int,
        username: Optional[str] = None,
        api_token: Optional[str] = None
    ) -> str:
        """Fetch console log from Jenkins API"""
        # Handle job names with folders
        job_path = job_name.replace('/', '/job/')
        url = f"{jenkins_url}/job/{job_path}/{build_number}/consoleText"
        
        auth = None
        if username and api_token:
            auth = HTTPBasicAuth(username, api_token)
        
        # Get timeout from config or use default
        try:
            from api.config.loader import CONFIG
            timeout = CONFIG.get('build_analysis', {}).get('timeout_seconds', 30)
        except Exception:
            timeout = 30
        
        logger.info(f"Fetching from: {url}")
        response = requests.get(url, auth=auth, timeout=timeout)
        response.raise_for_status()
        
        return response.text
    
    def _classify_error(self, log: str) -> str:
        """Classify the type of error from log content"""
        # Order matters - more specific patterns first
        error_patterns = {
            'out_of_memory': ['outofmemoryerror', 'java heap space', 'gc overhead limit'],
            'null_pointer_exception': ['nullpointerexception', 'null pointer'],
            'dependency_error': ['could not resolve', 'artifact not found', 'failed to resolve', 'dependency'],
            'network_error': ['connection refused', 'unknown host', 'connect timed out', 'no route to host'],
            'timeout_error': ['timeout', 'timed out', 'deadline exceeded'],
            'permission_error': ['permission denied', 'access denied', 'unauthorized', 'forbidden'],
            'test_failure': ['test failed', 'junit', 'assertion failed', 'expected', 'but was'],
            'compilation_error': ['javac', 'compilation failed', 'cannot find symbol', 'compiler error'],
            'configuration_error': ['no such file', 'invalid configuration', 'config'],
        }
        
        log_lower = log.lower()
        for error_type, keywords in error_patterns.items():
            if any(keyword in log_lower for keyword in keywords):
                return error_type
        
        return 'unknown_error'
    
    def _search_similar_issues(self, error_message: str, top_k: int = 5) -> List[Dict]:
        """Search vector database for similar issues"""
        if not self.vector_store:
            logger.warning("No vector store configured, skipping similarity search")
            return []
        
        try:
            # Query FAISS for similar errors
            logger.info(f"Searching vector DB for: {error_message[:100]}")
            results = self.vector_store.similarity_search(
                error_message,
                k=top_k
            )
            
            similar_issues = []
            for doc in results:
                similar_issues.append({
                    'source': doc.metadata.get('source', 'Unknown'),
                    'title': doc.metadata.get('title', 'No title'),
                    'url': doc.metadata.get('url', ''),
                    'excerpt': doc.page_content[:300] + '...' if len(doc.page_content) > 300 else doc.page_content,
                    'relevance_score': doc.metadata.get('score', 0)
                })
            
            logger.info(f"Found {len(similar_issues)} similar issues")
            return similar_issues
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            return []
    
    async def _arun(self, query: str) -> str:
        """Async version - not implemented"""
        raise NotImplementedError("Async not supported for build_failure_analyzer")
