"""
Main entry point for the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chatbot
from api.config.loader import CONFIG

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    CONFIG["cors"]["allowed_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chatbot.router, prefix=CONFIG["api"]["prefix"])
