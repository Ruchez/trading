import requests
import json
from security_vault import SecurityVault

def inspect_content():
    vault = SecurityVault()
    key = vault.grok_key
    url = "https://api.x.ai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    payload = {
        "model": "grok-3",
        "messages": [
            {"role": "system", "content": "Return JSON: {'test': 'success'}"},
            {"role": "user", "content": "go"}
        ],
        "temperature": 0,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print("RAW CONTENT (repr):")
            print(repr(content))
            print("END")
            
            # Test the parsing logic
            try:
                if "```json" in content:
                    parsed = json.loads(content.split("```json")[1].split("```")[0].strip())
                else:
                    parsed = json.loads(content)
                print(f"PARSED SUCCESS: {parsed}")
            except Exception as e:
                print(f"PARSED FAILURE: {e}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_content()
