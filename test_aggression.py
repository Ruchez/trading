import MetaTrader5 as mt5
import json
from risk_engine import RiskEngine

def test_risk_logic():
    print("--- 🛡️ Risk Engine Logic Test ---")
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    risk = RiskEngine(config)
    
    # 1. Test Gold Parameters
    print("\n[TEST] Gold Symbol (XAUUSD)")
    gold_lots, gold_pos = risk.get_session_params("XAUUSD", "SCALPER")
    print(f"Scalp -> Lots: {gold_lots} (Expect 0.01-0.02), Pos: {gold_pos} (Expect 10)")
    
    gold_lots_i, gold_pos_i = risk.get_session_params("XAUUSD", "INTRADAY")
    print(f"Intraday -> Lots: {gold_lots_i} (Expect 0.01-0.02), Pos: {gold_pos_i} (Expect 2)")

    # 2. Test Currency Parameters
    print("\n[TEST] Currency Symbol (GBPUSD)")
    fx_lots, fx_pos = risk.get_session_params("GBPUSD", "SCALPER")
    print(f"Scalp -> Lots: {fx_lots} (Expect 0.05-0.10), Pos: {fx_pos} (Expect 20)")
    
    fx_lots_i, fx_pos_i = risk.get_session_params("GBPUSD", "INTRADAY")
    print(f"Intraday -> Lots: {fx_lots_i} (Expect 0.05-0.10), Pos: {fx_pos_i} (Expect 5)")

    print("\n--- Logic Check Complete ---")

if __name__ == "__main__":
    if mt5.initialize():
        test_risk_logic()
        mt5.shutdown()
    else:
        print("MT5 Not running. Running simulation mode.")
        test_risk_logic()
