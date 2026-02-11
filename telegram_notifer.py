import requests
from security_vault import SecurityVault

class TelegramNotifier:
    """
    Handles outbound notifications to the user for 'Thoughts' and trade updates.
    """
    def __init__(self):
        self.vault = SecurityVault()
        # Primary
        self.creds = [
            {"token": self.vault.tg_token, "chat_id": self.vault.tg_chat_id}
        ]
        # Secondary (Optional)
        if self.vault.tg_token_2 and self.vault.tg_chat_id_2:
            self.creds.append({"token": self.vault.tg_token_2, "chat_id": self.vault.tg_chat_id_2})
            
        self.active = any(c['token'] and c['chat_id'] for c in self.creds)

    def send_message(self, message):
        """
        Sends a plain text message to all active users.
        """
        if not self.active:
            print(f"[LOG] {message}")
            return False

        any_success = False
        for cred in self.creds:
            if not cred['token'] or not cred['chat_id']:
                continue
                
            url = f"https://api.telegram.org/bot{cred['token']}/sendMessage"
            payload = {
                "chat_id": cred['chat_id'],
                "text": message,
                "parse_mode": "Markdown"
            }
            
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    any_success = True
                else:
                    print(f"[ERROR] Telegram ({cred['chat_id']}) responded with {response.status_code}: {response.text}")
            except Exception as e:
                print(f"[ERROR] Telegram ({cred['chat_id']}) Notification Failed: {e}")
        
        return any_success

    def send_thought(self, symbol, reasoning, conviction, mode="INTRADAY"):
        """
        Formatted notification for the bot's 'Institutional Intelligence'.
        """
        conv_emoji = "💎" if conviction > 85 else "🦾" if conviction > 70 else "⚖️"
        header = "🏛️ *INSTITUTIONAL ANALYSIS*" if mode == "INTRADAY" else "🚀 *SCALP SESSION COCKPIT*"
        
        msg = f"{header}\n"
        msg += f"Asset: `{symbol}` | Confidence: `{conviction}%` {conv_emoji}\n\n"
        msg += f"> {reasoning}"
        return self.send_message(msg)

    def send_trade_alert(self, symbol, action, price, mode="INTRADAY", session_count=None):
        """
        Elite notification for trade execution.
        """
        emoji = "💼" if action == "BUY" else "📉"
        header = f"*POSITION OPENED*" if mode == "INTRADAY" else f"*SESSION BURST ({session_count})*"
        
        msg = f"{emoji} {header}\n"
        msg += f"Symbol: `{symbol}`\n"
        msg += f"Action: `{action}` @ `{price}`\n"
        msg += f"Type: `{mode}`"
        return self.send_message(msg)
