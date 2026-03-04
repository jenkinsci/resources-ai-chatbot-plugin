import sys
from unittest.mock import MagicMock

# Mock heavy/missing dependencies
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['rag.embedding.embedding_model'] = MagicMock()
sys.modules['api.models.embedding_model'] = MagicMock()
sys.modules['api.models.llama_cpp_provider'] = MagicMock()

import os
# Add chatbot-core to path
chatbot_core_path = os.path.join(os.getcwd(), "chatbot-core")
if os.path.isdir(chatbot_core_path):
    sys.path.append(chatbot_core_path)
    os.chdir(chatbot_core_path)
    sys.path.append(os.getcwd())
else:
    sys.path.append(os.getcwd())

from api.models.schemas import FileAttachment
from api.tools.tools import analyze_jenkins_logs
import logging

# Setup dummy logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def test_log_analysis():
    print("Testing analyze_jenkins_logs tool...")
    
    # Mock files
    files = [
        FileAttachment(filename="build.log", content="ERROR: Build failed because of OutOfMemoryError", file_type="text/plain", size=100),
        FileAttachment(filename="readme.txt", content="Some other content", file_type="text/plain", size=50)
    ]
    
    result = analyze_jenkins_logs(query="Why did it fail?", logger=logger, files=files)
    print(f"Result:\n{result}")
    
    assert "OutOfMemoryError" in result
    print("Test passed!")

if __name__ == "__main__":
    try:
        test_log_analysis()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
