import requests
import sys

if len(sys.argv) < 2:
    print("Usage: python nuke_payload.py <SESSION_ID>")
    sys.exit(1)

session_id = sys.argv[1]
url = f"http://127.0.0.1:8000/api/chatbot/sessions/{session_id}/message"
headers = {"Content-Type": "application/json"}

print("Generating 500,000 character payload...")
massive_string = "A" * 500000 
payload = {"message": massive_string}

print("Firing payload...")
try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Server responded with HTTP {response.status_code}")
    print("Response snippet:", response.text[:200])
except Exception as e:
    print(f"Request failed: {e}")