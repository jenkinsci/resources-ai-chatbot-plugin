"""Ensure the chatbot-core package directory is importable as top-level modules."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
CHATBOT_CORE_DIR = ROOT_DIR / "chatbot-core"

if CHATBOT_CORE_DIR.exists():
    chat_core_path = str(CHATBOT_CORE_DIR)
    if chat_core_path not in sys.path:
        sys.path.insert(0, chat_core_path)
