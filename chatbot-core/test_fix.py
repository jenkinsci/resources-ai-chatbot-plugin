
import asyncio
from fastapi import HTTPException
from api.routes.chatbot import chatbot_reply
from api.models.schemas import ChatRequest

# Mocking dependencies
class MockBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        print(f"Background task added: {func.__name__} with args: {args}")
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Background task caught exception: {e}")

class MockRequest:
    def __init__(self, message):
        self.message = message

# Mock session existence and reply
import api.routes.chatbot as chatbot_module
chatbot_module.session_exists = lambda sid: True
chatbot_module.get_chatbot_reply = lambda sid, msg, files=None: {"response": f"Echo: {msg}"}
chatbot_module.persist_session = lambda sid: print(f"Persisting session {sid}")

def test_empty_message():
    print("\nRunning test_empty_message...")
    try:
        chatbot_reply("session_123", MockRequest("   "), MockBackgroundTasks())
        print("FAIL: Should have raised HTTPException for empty message")
    except HTTPException as e:
        print(f"PASS: Caught expected exception: {e.detail}")
    except Exception as e:
        print(f"FAIL: Caught unexpected exception: {e}")

def test_valid_message():
    print("\nRunning test_valid_message...")
    try:
        response = chatbot_reply("session_123", MockRequest("Hello"), MockBackgroundTasks())
        print(f"PASS: Got response: {response}")
    except Exception as e:
        print(f"FAIL: Caught unexpected exception: {e}")

def test_background_task_error():
    print("\nRunning test_background_task_error...")
    # Mock persist_session to fail
    chatbot_module.persist_session = lambda sid: 1 / 0
    
    try:
        response = chatbot_reply("session_123", MockRequest("Hello"), MockBackgroundTasks())
        print(f"PASS: Request succeeded despite background task failure. Response: {response}")
    except Exception as e:
        print(f"FAIL: Background task failure crashed the request: {e}")

if __name__ == "__main__":
    test_empty_message()
    test_valid_message()
    test_background_task_error()
