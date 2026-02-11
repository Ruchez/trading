import requests
import time
import MetaTrader5 as mt5

class TelegramCommander:
    """
    Listens for and executes remote commands sent via Telegram.
    Allows for system stops, resumes, and panic liquidations.
    """
    def __init__(self, bridge, risk_engine, notifier):
        self.bridge = bridge
        self.risk_engine = risk_engine
        self.notifier = notifier
        self.last_update_id = 0
        self.is_stopped = False
        self.pending_learning_trigger = False
        self.vault = notifier.vault
        
        # Authorized IDs
        self.allowed_ids = [
            int(self.vault.tg_chat_id) if self.vault.tg_chat_id else 0,
            int(self.vault.tg_chat_id_2) if self.vault.tg_chat_id_2 else 0
        ]
        self.allowed_ids = [i for i in self.allowed_ids if i != 0]

    def poll_commands(self):
        """
        Check for new messages and process recognized commands.
        Non-blocking.
        """
        token = self.vault.tg_token
        if not token: return
        
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 0}
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    self.last_update_id = update["update_id"]
                    if "message" in update:
                        self._process_message(update["message"])
        except Exception as e:
            print(f"[ERROR] Telegram Polling Failed: {e}")

    def _process_message(self, message):
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        if chat_id not in self.allowed_ids:
            print(f"[SECURITY] Unauthorized command attempt from {chat_id}")
            return

        command = text.split()[0].lower() if text else ""
        
        if command == "/stop":
            self.is_stopped = True
            self.notifier.send_message("🛑 *SYSTEM HALTED*\nBot will stop scanning for new signals.")
            
        elif command == "/resume":
            self.is_stopped = False
            self.notifier.send_message("🚀 *SYSTEM RESUMED*\nBot is back to scanning markets.")
            
        elif command == "/panic":
            positions = mt5.positions_get()
            if positions:
                for pos in positions:
                    self.bridge.close_position(pos.ticket)
                self.notifier.send_message(f"🧨 *PANIC BUTTON PRESSED*\nClosed {len(positions)} positions immediately.")
            else:
                self.notifier.send_message("🤷 *Nothing to close.*")

        elif command == "/learn":
            self.notifier.send_message("🧠 *AI INTERVENTION*\nAnalyzing current open trades to identify mistakes...")
            # This flag will be picked up by the main loop
            self.pending_learning_trigger = True
                
        elif command == "/status":
            acc = mt5.account_info()
            if acc:
                pos_count = mt5.positions_total()
                msg = f"📊 *System Status*\n"
                msg += f"State: {'🔴 STOPPED' if self.is_stopped else '🟢 RUNNING'}\n"
                msg += f"Balance: ${acc.balance:,.2f}\n"
                msg += f"Equity: ${acc.equity:,.2f}\n"
                msg += f"Profit: ${acc.profit:,.2f}\n"
                msg += f"Open Pos: {pos_count}"
                self.notifier.send_message(msg)
