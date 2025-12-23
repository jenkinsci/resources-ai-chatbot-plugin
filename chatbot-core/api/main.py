"""
Main entry point for the FastAPI application.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chatbot
from api.config.loader import CONFIG
from api.services.memory import cleanup_expired_sessions
from api.utils.logger import logger


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
    logger.info("Application shutdown complete, background tasks stopped")


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CONFIG["cors"]["allowed_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chatbot.router, prefix=CONFIG["api"]["prefix"])
