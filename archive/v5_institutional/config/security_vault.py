"""
Security Vault - Credential Management
Loads API keys and credentials from .env file
"""
import os
from dotenv import load_dotenv

class SecurityVault:
    def __init__(self):
        load_dotenv()
        self.login = int(os.getenv('MT5_LOGIN', 0))
        self.password = os.getenv('MT5_PASSWORD', '')
        self.server = os.getenv('MT5_SERVER', '')
        self.tg_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.tg_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.tg_token_2 = os.getenv('TELEGRAM_BOT_TOKEN_2', '')
        self.tg_chat_id_2 = os.getenv('TELEGRAM_CHAT_ID_2', '')
        self.grok_key = os.getenv('GROK_API_KEY', '')
        self.gemini_key = os.getenv('GEMINI_API_KEY', '')
        
    def get_credentials(self):
        """Get MT5 login credentials"""
        return {
            'login': self.login,
            'password': self.password,
            'server': self.server
        }
    
    def validate(self):
        """Validate that credentials are set"""
        if not self.login or not self.password or not self.server:
            print("❌ MT5 credentials missing in .env file")
            return False
        return True
    
    def get_telegram_token(self):
        """Get Telegram bot token"""
        return self.tg_token
    
    def get_telegram_chat_id(self):
        """Get Telegram chat ID"""
        return self.tg_chat_id
    
    def get_grok_api_key(self):
        """Get Grok API key"""
        return self.grok_key
    
    def get_gemini_api_key(self):
        """Get Gemini API key"""
        return self.gemini_key
