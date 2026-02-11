import os
from dotenv import load_dotenv

class SecurityVault:
    def __init__(self):
        load_dotenv()
        self.login = int(os.getenv("MT5_LOGIN", 0))
        self.password = os.getenv("MT5_PASSWORD", "")
        self.server = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
        
        # AI Keys
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.grok_key = os.getenv("GROK_API_KEY", "")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        
        # Telegram
        self.tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.tg_token_2 = os.getenv("TELEGRAM_BOT_TOKEN_2", "")
        self.tg_chat_id_2 = os.getenv("TELEGRAM_CHAT_ID_2", "")

        print(f"[DEBUG] Vault Loaded - MT5: {self.server}, AI Keys: {'GEMINI ' if self.gemini_key else ''}{'GROK ' if self.grok_key else ''}")

    def validate(self):
        if self.login == 0:
            print("[CRITICAL] MT5_LOGIN not set in .env file.")
            return False
        if not self.gemini_key:
            print("[WARNING] GEMINI_API_KEY not set. Thinking mode will be limited.")
        return True

    def get_credentials(self):
        return {
            "login": self.login,
            "password": self.password,
            "server": self.server
        }
