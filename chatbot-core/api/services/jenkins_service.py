"""
Service for interacting with the Jenkins API.
"""

import os
import logging
import requests
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def fetch_build_log(build_number: str, job_name: str = "default-job") -> Optional[str]:
    """
    Fetches the console text for a specific Jenkins build.
    
    Reads Jenkins configuration from environment variables:
    - JENKINS_URL: The base URL of the Jenkins server
    - JENKINS_USER: The Jenkins username (optional, for auth)
    - JENKINS_API_TOKEN: The Jenkins API token (optional, for auth)
    
    Args:
        build_number (str): The build number (e.g., '42').
        job_name (str): The name of the Jenkins job.
        
    Returns:
        Optional[str]: The console text of the build, or None if failed.
    """
    jenkins_url = os.environ.get("JENKINS_URL", "http://localhost:8080")
    username = os.environ.get("JENKINS_USER")
    api_token = os.environ.get("JENKINS_API_TOKEN")
    
    # Strip the # if the user passed it
    build_number = build_number.lstrip('#')
    
    # Construct the endpoint URL for the console text
    endpoint = f"/job/{job_name}/{build_number}/consoleText"
    url = urljoin(jenkins_url, endpoint)
    
    logger.info("Fetching build log from: %s", url)
    
    auth = None
    if username and api_token:
        auth = (username, api_token)
        
    try:
        # We only need the text, no json parsing
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 404:
            logger.warning("Build log not found for job '%s' build '%s'", job_name, build_number)
            return None
            
        response.raise_for_status()
        return response.text
        
    except requests.RequestException as e:
        logger.error("Failed to fetch Jenkins build log: %s", e)
        return None
