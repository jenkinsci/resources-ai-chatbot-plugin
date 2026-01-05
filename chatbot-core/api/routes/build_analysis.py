"""
API endpoints for build failure analysis
Provides REST API for analyzing Jenkins build failures
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from urllib.parse import urlparse
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/build-analysis", tags=["Build Analysis"])


def _validate_jenkins_url(url: str) -> bool:
    """
    Validate Jenkins URL to prevent SSRF attacks
    
    Args:
        url: Jenkins URL to validate
        
    Returns:
        True if URL is safe, False otherwise
    """
    if not url:
        return True  # Will use config default
    
    try:
        parsed = urlparse(url)
        
        # Must use http or https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Block internal/private IPs and metadata endpoints
        blocked_hosts = [
            'localhost', '127.0.0.1', '0.0.0.0',
            '169.254.169.254',  # AWS metadata
            '::1', '[::]'  # IPv6 localhost
        ]
        
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Check if hostname is blocked
        if hostname.lower() in blocked_hosts:
            return False
        
        # Block private IP ranges (basic check)
        if hostname.startswith('10.') or hostname.startswith('192.168.') or hostname.startswith('172.'):
            # These are private IP ranges - require explicit allowlist
            return False
        
        return True
        
    except Exception:
        return False


class BuildAnalysisRequest(BaseModel):
    """Request model for build failure analysis"""
    job_name: str = Field(..., description="Name of the Jenkins job")
    build_number: int = Field(..., description="Build number to analyze")
    jenkins_url: Optional[str] = Field(None, description="Jenkins URL (uses config default if not provided)")
    username: Optional[str] = Field(None, description="Jenkins username (uses config default if not provided)")
    api_token: Optional[str] = Field(None, description="Jenkins API token (uses config default if not provided)")


class SimilarIssue(BaseModel):
    """Model for similar issues found in vector database"""
    source: str
    title: str
    url: str
    excerpt: str
    relevance_score: float = 0.0


class BuildAnalysisResponse(BaseModel):
    """Response model for build failure analysis"""
    status: str
    job_name: str
    build_number: int
    error_type: str
    error_message: str
    log_summary: str
    sanitized_log: str
    similar_issues: List[SimilarIssue]
    redacted_fields: List[str]
    total_similar_issues: int
    suggested_fix: Optional[str] = None


@router.post("/analyze", response_model=BuildAnalysisResponse)
async def analyze_build_failure(request: BuildAnalysisRequest):
    """
    Analyze a failed Jenkins build
    
    This endpoint:
    1. Fetches the console log from Jenkins
    2. Sanitizes PII and sensitive data (CRITICAL for security)
    3. Extracts error context
    4. Searches vector database for similar issues
    5. Provides analysis and suggestions
    
    Args:
        request: Build analysis request with job name and build number
        
    Returns:
        BuildAnalysisResponse with analysis results and similar issues
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Import here to avoid circular dependencies
        from api.services.tools.build_failure_analyzer import BuildFailureAnalyzer
        from api.config.loader import get_config
        
        config = get_config()
        
        # Validate Jenkins URL to prevent SSRF
        if request.jenkins_url and not _validate_jenkins_url(request.jenkins_url):
            raise HTTPException(
                status_code=400,
                detail="Invalid Jenkins URL. Use configured Jenkins instance or provide a valid external URL."
            )
        
        # Note: Vector store integration would require FAISS index to be loaded
        # For now, we pass None and the tool will skip similarity search
        # To enable: load the FAISS index from rag.retriever.retriever_utils
        vector_store = None
        logger.info("Vector store not loaded - similarity search will be skipped")
        
        # Use configured URL if not provided, or validate provided URL
        jenkins_url = request.jenkins_url or config.get('jenkins', {}).get('url')
        
        # Create analyzer with configuration
        analyzer = BuildFailureAnalyzer(
            jenkins_url=jenkins_url,
            username=request.username or config.get('jenkins', {}).get('username'),
            api_token=request.api_token or config.get('jenkins', {}).get('api_token'),
            vector_store=vector_store
        )
        
        # Prepare query for the tool
        query = json.dumps({
            'job_name': request.job_name,
            'build_number': request.build_number,
            'jenkins_url': analyzer.jenkins_url,
            'username': analyzer.username,
            'api_token': analyzer.api_token
        })
        
        logger.info(f"Analyzing build {request.job_name} #{request.build_number}")
        
        # Run analysis
        result = analyzer._run(query)
        analysis = json.loads(result)
        
        if analysis['status'] == 'error':
            raise HTTPException(status_code=500, detail=analysis['message'])
        
        # Generate suggested fix based on error type
        suggested_fix = _generate_fix_suggestion(
            analysis['error_type'],
            analysis['sanitized_log'],
            analysis.get('similar_issues', [])
        )
        
        # Convert similar issues to proper model
        similar_issues = [
            SimilarIssue(**issue) for issue in analysis.get('similar_issues', [])
        ]
        
        return BuildAnalysisResponse(
            status=analysis['status'],
            job_name=analysis['job_name'],
            build_number=analysis['build_number'],
            error_type=analysis['error_type'],
            error_message=analysis['error_message'],
            log_summary=analysis['error_message'],
            sanitized_log=analysis['sanitized_log'],
            similar_issues=similar_issues,
            redacted_fields=analysis.get('redacted_fields', []),
            total_similar_issues=analysis.get('total_similar_issues', 0),
            suggested_fix=suggested_fix
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def _generate_fix_suggestion(error_type: str, log: str, similar_issues: List[Dict]) -> str:
    """
    Generate contextual fix suggestions based on error type and similar issues
    
    Args:
        error_type: Classified error type
        log: Sanitized log content
        similar_issues: Similar issues found in knowledge base
        
    Returns:
        Suggested fix as markdown text
    """
    
    # Base suggestions by error type
    base_suggestions = {
        'compilation_error': """
## Compilation Error Detected

**Common Causes:**
- Syntax errors in source code
- Missing imports or undefined classes
- Java version incompatibility

**Recommended Actions:**
1. Check the error message for the specific file and line number
2. Verify all required classes are imported
3. Ensure Java version in `pom.xml` or `build.gradle` matches your code
4. Run `mvn clean compile` locally to reproduce the issue
        """,
        
        'test_failure': """
## Test Failure Detected

**Common Causes:**
- Assertion mismatches (expected vs actual values)
- Test data or mock configuration issues
- Environment-specific failures

**Recommended Actions:**
1. Review the failed test assertions in the log
2. Check if test data or mocks are properly configured
3. Verify environment-specific configurations (database, API endpoints)
4. Run the specific test locally: `mvn test -Dtest=TestClassName`
        """,
        
        'dependency_error': """
## Dependency Resolution Error

**Common Causes:**
- Missing or incorrect dependency versions in build file
- Repository URLs are inaccessible
- Version conflicts between dependencies
- Corrupted local cache

**Recommended Actions:**
1. Check your `pom.xml` or `build.gradle` for correct dependencies
2. Verify repository URLs are accessible
3. Clear local cache: `mvn clean` or `gradle clean --refresh-dependencies`
4. Check for version conflicts using `mvn dependency:tree`
        """,
        
        'null_pointer_exception': """
## NullPointerException Detected

**Common Causes:**
- Accessing properties/methods on null objects
- Uninitialized variables or objects
- Missing null checks
- Configuration values that are null

**Recommended Actions:**
1. Identify the line number from the stack trace
2. Add null checks before accessing object properties
3. Verify object initialization in your code
4. Check configuration values that might be null
5. Use Optional<T> for nullable return values
        """,
        
        'permission_error': """
## Permission Error Detected

**Common Causes:**
- Jenkins lacks file system permissions
- SCM credentials not configured
- Workspace permission issues

**Recommended Actions:**
1. Verify Jenkins has proper file system permissions
2. Check SCM credentials in Jenkins configuration
3. Review workspace cleanup settings
4. Ensure the Jenkins user has access to required directories
        """,
        
        'timeout_error': """
## Timeout Error Detected

**Common Causes:**
- Long-running processes exceeding time limits
- Network connectivity issues
- Resource contention

**Recommended Actions:**
1. Increase timeout values in Jenkins job configuration
2. Check network connectivity to external services
3. Review long-running processes in your build
4. Consider parallelizing slow operations
        """,
        
        'out_of_memory': """
## Out of Memory Error

**Common Causes:**
- Insufficient heap space allocated
- Memory leaks in code
- Too many parallel processes

**Recommended Actions:**
1. Increase heap size: Add `-Xmx2g` to `MAVEN_OPTS` or `GRADLE_OPTS`
2. Review memory-intensive operations in your build
3. Check for memory leaks in your code
4. Reduce parallel test execution
        """,
        
        'network_error': """
## Network Error Detected

**Common Causes:**
- Connection to external services failed
- DNS resolution issues
- Firewall or proxy blocking connections

**Recommended Actions:**
1. Verify external service URLs are accessible
2. Check DNS resolution for hostnames
3. Review firewall and proxy settings
4. Add retry logic for transient network failures
        """,
        
        'configuration_error': """
## Configuration Error Detected

**Common Causes:**
- Missing configuration files
- Invalid configuration values
- File path issues

**Recommended Actions:**
1. Verify all required configuration files exist
2. Check file paths are correct (absolute vs relative)
3. Validate configuration syntax
4. Ensure configuration values match expected format
        """,
        
        'unknown_error': """
## Build Error Detected

**Recommended Actions:**
1. Review the error log above for specific details
2. Check the full console output in Jenkins
3. Search for the error message in the similar issues below
4. Try reproducing the build locally
        """
    }
    
    suggestion = base_suggestions.get(error_type, base_suggestions['unknown_error'])
    
    # Add information about similar issues if found
    if similar_issues:
        suggestion += "\n\n## Similar Issues Found in Knowledge Base\n\n"
        suggestion += f"Found {len(similar_issues)} similar issues that might help:\n\n"
        
        for i, issue in enumerate(similar_issues[:3], 1):  # Show top 3
            suggestion += f"{i}. **{issue.get('title', 'Untitled')}**\n"
            if issue.get('url'):
                suggestion += f"   - Source: {issue.get('source', 'Unknown')} - [{issue['url']}]({issue['url']})\n"
            suggestion += f"   - {issue.get('excerpt', 'No description')[:150]}...\n\n"
    else:
        suggestion += "\n\n_No similar issues found in knowledge base. The error might be unique to your setup._\n"
    
    return suggestion


@router.get("/health")
async def health_check():
    """Health check endpoint for build analysis service"""
    return {
        "status": "healthy",
        "service": "build-analysis",
        "version": "1.0.0"
    }
