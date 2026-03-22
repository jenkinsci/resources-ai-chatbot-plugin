"""
Jenkins API Service
Handles communication with the live Jenkins instance to retrieve runtime data (logs, status).
"""
import logging
from typing import Optional
from api.config.loader import CONFIG

logger = logging.getLogger(__name__)

# Temporary mock data for Agentic Architecture simulation when real Jenkins is unreachable
MOCK_LOGS = """
Started by user admin
Running as SYSTEM
Building in workspace /var/lib/jenkins/workspace/test-pipeline
[test-pipeline] $ /bin/sh -xe /tmp/jenkins834923492.sh
+ npm install
npm ERR! code EUSAGE
npm ERR! 
npm ERR! The `npm install` command requires a package.json file, but none was found.
npm ERR! A complete log of this run can be found in: /root/.npm/_logs/2026-03-20T10_00_00_000Z-debug-0.log
Build step 'Execute shell' marked build as failure
Finished: FAILURE
"""

class JenkinsAPIClient:
    def __init__(self):
        self.jenkins_config = CONFIG.get("jenkins", {})
        self.url = self.jenkins_config.get("url", "http://localhost:8080")
        self.user = self.jenkins_config.get("user", "")
        self.token = self.jenkins_config.get("token", "")
        self.simulate = self.jenkins_config.get("simulate_runtime_data", True)

    def get_recent_failed_build_logs(self, job_name: Optional[str] = None) -> str:
        """
        Retrieves logs from the most recent failed build.
        In a real implementation, this would make an HTTP request to Jenkins REST API.
        """
        logger.info(f"Retrieving recent build logs from Jenkins for job: {job_name or 'any'}")
        
        if self.simulate:
            logger.info("Using simulated runtime data (logs) for Agent 3.")
            return MOCK_LOGS
            
        # TODO: Implement actual requests.get() to Jenkins API
        # response = requests.get(f"{self.url}/job/{job_name}/lastFailedBuild/consoleText", auth=(self.user, self.token))
        return "No recent logs available or Jenkins unreachable."

# Singleton instance
jenkins_client = JenkinsAPIClient()
