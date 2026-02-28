"""
Elite Agentic Trading System - Launcher
Entry point for the restored modular architecture.
"""
import sys
import os

# Add project root and src to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

def banner():
    print("=" * 60)
    print("      🏛️  INSTITUTIONAL AGENTIC TRADING SYSTEM V5  🏛️")
    print("=" * 60)
    print(f"Project Home: {root_dir}")
    print("Mode: Quality Over Quantity (Institutional Evolution)")
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
