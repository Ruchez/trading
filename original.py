"""
Elite Agentic Trading System - Launcher
Entry point for the restored modular architecture.
"""
import sys
import os

# Fix Unicode Encoding for emojis in standard windows terminals
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add archive path to sys.path to run the original V5 institutional logic
root_dir = os.path.dirname(os.path.abspath(__file__))
archive_path = os.path.join(root_dir, 'archive', 'v5_institutional')

# Priority pathing: ensure archive takes precedence over root src
sys.path.insert(0, archive_path)

def banner():
    print("=" * 60)
    print("      🏛️  [ARCHIVE] INSTITUTIONAL TRADING SYSTEM V5  🏛️")
    print("=" * 60)
    print(f"Project Home: {root_dir}")
    print(f"Archive Path: {archive_path}")
    print("Mode: Original V5 Logic (Self-Contained Archive)")
    print("-" * 60)

def start():
    banner()
    try:
        from src.main_loop import main
        main()
    except Exception as e:
        print(f"❌ CRITICAL FAILURE DURING BOOTSTRAP: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        print("\n👋 System shutdown by operator.")
