import requests
import json
import traceback
from security_vault import SecurityVault

def verbose_debug_grok():
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
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Return the word 'HELLO' in JSON: {'word': 'HELLO'}"}
        ],
        "temperature": 0,
        "stream": False
    }
    
    print(f"--- 🩺 Verbose Grok Diagnostic ---")
    print(f"URL: {url}")
    print(f"Key (First 10 chars): {key[:10]}...")
    
    try:
        print("\nSending POST request...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Response Body:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"\n❌ FAILED! Error Body:")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out (15s limit).")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Connection Error. {e}")
    except Exception:
        print("\n❌ UNEXPECTED ERROR:")
        traceback.print_exc()

if __name__ == "__main__":
    verbose_debug_grok()
