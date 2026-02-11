import requests
import time
import os
from dotenv import load_dotenv

def get_id_from_message():
    load_dotenv()
    # Focus ONLY on the new bot token for the friend
    token = os.getenv("TELEGRAM_BOT_TOKEN_2")
    user_id_to_ignore = 7701821501 
    
    if not token or ":" not in token:
        print("[FAIL] TELEGRAM_BOT_TOKEN_2 is empty in .env. Please add your friend's token first!")
        return

    print("--- 🔍 Friend ID Finder ---")
    print(f"Listening to secondary bot (Token starting with {token[:5]})...")
    print(f"1. Your friend MUST open THEIR new bot.")
    print(f"2. Your friend MUST click 'START' and type 'hello'.")
    print(f"\nSearching (I will ignore messages from you)...")

    offset = 0
    start_time = time.time()
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    while time.time() - start_time < 120:
        try:
            response = requests.get(url, params={"offset": offset, "timeout": 5})
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        
                        # IGNORE YOUR ID
                        if chat_id == user_id_to_ignore:
                            offset = update["update_id"] + 1
                            continue
                            
                        user_name = update["message"]["from"].get("first_name", "User")
                        print(f"\n✅ FOUND YOUR FRIEND!")
                        print(f"From User: {user_name}")
                        print(f"YOUR FRIEND'S CHAT_ID: {chat_id}")
                        print(f"\nCopy the number {chat_id} and put it in your .env file!")
                        return
                    offset = update["update_id"] + 1
        except:
            pass
        time.sleep(1)
    
    print("\n[TIMEOUT] I didn't see any messages. Make sure the tokens are correct and the user clicked 'START'.")

if __name__ == "__main__":
    get_id_from_message()
