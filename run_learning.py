import json
from ai_brain import AIBrain

def demo_learning():
    print("--- 🧠 AI Learning Engine Demonstration ---")
    brain = AIBrain()
    
    # Mock Data: A Gold trade that hit SL
    symbol = "XAUUSD"
    entry_snapshot = "Trend: Bullish | RSI: 35 (Oversold) | Order Block: H1 Bullish OB | Sentiment: Institutional Buy Influx."
    exit_snapshot = "Rejection at 2045 Resistance | Massive Institutional Sell Imbalance in London Open | Trend flipped Bearish."
    pnl = -150.50
    
    print(f"\n[STEP 1] Mocking a Failed Trade: {symbol} (PnL: ${pnl})")
    print(f"Entry Context: {entry_snapshot}")
    print(f"Exit Context: {exit_snapshot}")
    
    print("\n[STEP 2] Triggering Post-Mortem Analysis...")
    analysis = brain.analyze_loss(symbol, entry_snapshot, exit_snapshot, pnl)
    
    if analysis:
        print(f"\n✅ AI MISTAKE IDENTIFIED: {analysis.get('mistake')}")
        print(f"✅ LESSON LEARNED: {analysis.get('lesson')}")
        
        print("\n[STEP 3] Verifying Memory Injection...")
        setup_logic = brain.analyze_setup("New Gold Setup (H1 Bullish OB)")
        print(f"\nAI's Decision with Memory: {setup_logic.get('action')}")
        print(f"AI's Reasoning: {setup_logic.get('reasoning')}")
    else:
        print("\n[FAIL] AI analysis failed. Check API key.")

if __name__ == "__main__":
    demo_learning()
