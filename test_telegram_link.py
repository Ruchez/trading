import requests
import os
from dotenv import load_dotenv

def test_telegram():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print("--- 📱 Telegram Connection Test ---")
    
    if not token or ":" not in token:
        print("[FAIL] TELEGRAM_BOT_TOKEN is missing or invalid in .env")
        return
        
    if not chat_id:
        print("[FAIL] TELEGRAM_CHAT_ID is missing in .env")
        return
        
    print(f"Testing with Token: {token[:10]}... (Total length: {len(token)})")
    print(f"Testing with Chat ID: {chat_id}")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "✅ *Connection Successful!*\nIf you see this message, your bot is correctly linked to your personal Telegram account.",
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("\n[SUCCESS] Message sent! Check your Telegram app.")
        else:
            print(f"\n[FAIL] Telegram responded with {response.status_code}")
            print(f"Error Details: {response.text}")
            
            if response.status_code == 401:
                print("Tip: Your BOT_TOKEN is probably wrong.")
            elif response.status_code == 400:
                print("Tip: Your CHAT_ID is probably wrong (should be a number, not your @username).")
            elif response.status_code == 403:
                print("Tip: Make sure you have clicked 'START' on your bot first.")
                
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")

if __name__ == "__main__":
    test_telegram()
