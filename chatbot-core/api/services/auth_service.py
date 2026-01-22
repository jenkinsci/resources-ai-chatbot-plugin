"""
Authentication Service.
Handles validation of Jenkins user identity headers and enforces login requirements.
"""
from fastapi import Header, HTTPException
from pydantic import BaseModel

# Header constants matching those injected by your Java ChatbotRootAction.java
HEADER_USER_ID = "X-Jenkins-User-ID"
HEADER_USER_NAME = "X-Jenkins-User-Name"

class JenkinsUser(BaseModel):
    """
    Domain model representing an authenticated Jenkins user.
    """
    user_id: str
    full_name: str

async def get_current_jenkins_user(
    x_jenkins_user_id: str = Header(..., alias=HEADER_USER_ID),
    x_jenkins_user_name: str = Header("Anonymous", alias=HEADER_USER_NAME)
) -> JenkinsUser:
    """
    FastAPI Dependency: Validates that the request contains the necessary
    identity headers injected by the Jenkins Java Proxy.

    ENFORCEMENT: Rejects 'anonymous' users with 403 Forbidden.
    """
    if not x_jenkins_user_id:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers. Request must come through Jenkins proxy."
        )

    # STRICTLY BLOCK ANONYMOUS ACCESS
    if x_jenkins_user_id.lower() == "anonymous":
        raise HTTPException(
            status_code=403,
            detail="Authentication required. Please log in to Jenkins to use the chatbot."
        )

    return JenkinsUser(user_id=x_jenkins_user_id, full_name=x_jenkins_user_name)