from telegram_notifer import TelegramNotifier
import time

def verify_dual_bots():
    print("--- 📱 Dual Telegram Verification ---")
    notifier = TelegramNotifier()
    
    if not notifier.active:
        print("[FAIL] No active Telegram credentials found in .env")
        return

    print(f"Detected {len(notifier.creds)} active notification channels.")
    
    test_msg = "🎊 *Dual Bot Sync Successful!*\nBoth you and your partner are now receiving real-time AI thoughts from the Institutional Trading Engine."
    
    success = notifier.send_message(test_msg)
    
    if success:
        print("\n[SUCCESS] Test messages sent! Check both Telegram accounts.")
    else:
        print("\n[FAIL] Messages failed to send. Check console for error details.")

if __name__ == "__main__":
    verify_dual_bots()
