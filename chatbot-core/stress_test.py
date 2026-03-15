import threading
import requests
import sys

if len(sys.argv) < 2:
    print("Usage: python stress_test.py <SESSION_ID>")
    sys.exit(1)

session_id = sys.argv[1]
url = f"http://127.0.0.1:8000/api/chatbot/sessions/{session_id}/message"
headers = {"Content-Type": "application/json"}

def fire_payload(thread_id):
    payload = {"message": f"Concurrency Test {thread_id}"}
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Thread {thread_id} returned HTTP {response.status_code}")
    except Exception as e:
        print(f"Thread {thread_id} failed: {e}")

threads = []
for i in range(1, 4):
    t = threading.Thread(target=fire_payload, args=(i,))
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()

print("Strike complete!")