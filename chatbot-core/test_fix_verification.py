from api.prompts.prompt_builder import build_prompt
from langchain.memory import ConversationBufferMemory

# 1. Setup mock data
user_query = "Why did my build fail?"
context = "Jenkins Pipeline documentation..."
memory = ConversationBufferMemory(return_messages=True)

# 2. Create a "poisoned" log with a secret
log_with_secret = "Error at line 45: password=MySecretPassword123 and aws_key=AKIAIOSFODNN7EXAMPLE"

print("--- Testing Prompt Generation ---")

# 3. Call your modified build_prompt function
final_prompt = build_prompt(
    user_query=user_query,
    context=context,
    memory=memory,
    log_context=log_with_secret
)

# 4. Check if the secrets are still there
if "MySecretPassword123" in final_prompt or "AKIAIOSFODNN7EXAMPLE" in final_prompt:
    print("❌ FAIL: Secrets were leaked into the prompt!")
    print("\nFull Prompt Output:\n", final_prompt)
else:
    print("✅ SUCCESS: Secrets were redacted!")
    print("\nSanitized Prompt Section:\n")
    # Print just the log section to verify
    for line in final_prompt.split('\n'):
        if "User-Provided Log Data:" in line or "[REDACTED]" in line:
            print(line.strip())