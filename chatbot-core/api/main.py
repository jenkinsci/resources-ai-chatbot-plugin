"""
Main entry point for the FastAPI application.
"""

import sys

def check_python_compatibility():
    """
    Prevents the application from running on unsupported Python versions 
    that cause cryptic C-level crashes in FAISS or ONNX.
    """
    # Python 3.14+ is currently unstable for our core C-extensions
    if sys.version_info >= (3, 14):
        print("=" * 60, file=sys.stderr)
        print("ERROR: UNSUPPORTED PYTHON VERSION", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        print("Python 3.14+ detected. This version is currently unsupported", file=sys.stderr)
        print("due to internal C-API changes affecting FAISS and ONNX.", file=sys.stderr)
        print("Please use Python 3.9 - 3.13 to ensure stability.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

# Run the check immediately
check_python_compatibility()

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chatbot
from api.config.loader import CONFIG
from api.services.memory import cleanup_expired_sessions, reload_persisted_sessions
from utils import LoggerFactory
from pydantic import BaseModel

logger = LoggerFactory.get_logger(__name__)


async def periodic_session_cleanup():
    """
    Background task that periodically cleans up expired sessions.
    """
    cleanup_interval = CONFIG.get("session", {}).get("cleanup_interval_seconds", 3600)
    logger.info("Starting periodic session cleanup task (interval: %ss)", cleanup_interval)

    while True:
        await asyncio.sleep(cleanup_interval)
        try:
            cleaned_count = cleanup_expired_sessions()
            if cleaned_count > 0:
                logger.info("Cleaned up %s expired session(s)", cleaned_count)
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.error("Error during session cleanup: %s", error)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):  # pylint: disable=unused-argument
    """
    Manages the application lifecycle, starting background tasks on startup.
    """
    loaded = reload_persisted_sessions()
    logger.info("Restored %s persisted session(s) from disk", loaded)

    # Startup: Create the cleanup task
    cleanup_task = asyncio.create_task(periodic_session_cleanup())
    logger.info("Application startup complete, background tasks initialized")

    yield

    # Shutdown: Cancel the cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Application shutdown complete")
    logger.info("Background tasks stopped")


# =========================
# Health Check Models
# =========================
class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    llm_available: bool


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["cors"]["allowed_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Health Check Endpoint
# =========================
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for container orchestration (Kubernetes, Docker, etc.).

    Returns:
        HealthResponse: Contains the service status and LLM availability.
    """
    llm_available = False
    try:
        # pylint: disable=import-outside-toplevel
        from api.models.llama_cpp_provider import llm_provider
        llm_available = llm_provider is not None
    except Exception:  # pylint: disable=broad-except
        pass

    return HealthResponse(
        status="healthy",
        llm_available=llm_available
    )


# Routes
app.include_router(chatbot.router, prefix=CONFIG["api"]["prefix"])
