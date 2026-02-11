import requests
import json
from security_vault import SecurityVault

def list_models():
    vault = SecurityVault()
    key = vault.grok_key
    url = "https://api.x.ai/v1/models"
    
    headers = {
        "Authorization": f"Bearer {key}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            models = response.json().get('data', [])
            ids = [m['id'] for m in models]
            print("Available Models:")
            with open("grok_models.txt", "w") as f:
                for m_id in ids:
                    print(m_id)
                    f.write(m_id + "\n")
            print("\nIDs saved to grok_models.txt")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    list_models()
