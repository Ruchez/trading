import requests
import json
from security_vault import SecurityVault

def debug_grok():
    vault = SecurityVault()
    key = vault.grok_key
    url = "https://api.x.ai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    models = ["grok-2", "grok-2-latest", "grok-beta", "grok-3"]
    
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Test for model: {model}. Say 'Success' if you receive this."}
            ],
            "temperature": 0,
            "stream": False
        }
        
        print(f"\n--- Testing Model: {model} ---")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Response JSON Content:")
                print(response.json()['choices'][0]['message']['content'])
            else:
                print(f"Error Response: {response.text}")
        except Exception as e:
            print(f"Request Exception: {e}")

if __name__ == "__main__":
    debug_grok()
