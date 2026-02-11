try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import pandas as pd
import numpy as np

def load_mock_data():
    """Generates mock data to test indicators without an MT5 connection."""
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=300, freq="H")
    data = pd.DataFrame({
        'time': dates,
        'open': np.linspace(2000, 2100, 300) + np.random.normal(0, 5, 300),
        'high': np.linspace(2010, 2110, 300) + np.random.normal(0, 5, 300),
        'low': np.linspace(1990, 2090, 300) + np.random.normal(0, 5, 300),
        'close': np.linspace(2005, 2105, 300) + np.random.normal(0, 5, 300),
    })
    # Force an FVG
    data.loc[250, 'low'] = 2150
    data.loc[250, 'high'] = 2160
    data.loc[248, 'high'] = 2100
    
    # Force a liquidity sweep
    data.loc[290, 'low'] = 1900 # Deep dip
    data.loc[290, 'close'] = 2100 # Quick recovery
    
    return data

def test_indicators():
    print("\n--- Testing Institutional Indicators ---")
    df = load_mock_data()
    
    fvgs = detect_fvg(df)
    print(f"FVG Detected: {len(fvgs)} found. Latest: {fvgs[-1] if fvgs else 'None'}")
    
    sweep = detect_liquidity_sweep(df)
    print(f"Liquidity Sweep Detection: {sweep}")
    
    zscore = calculate_zscore(df['close'])
    print(f"Z-Score (latest): {zscore.iloc[-1]:.2f}")

def test_regime_engine():
    print("\n--- Testing Regime Engine ---")
    df = load_mock_data()
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    engine = RegimeEngine(config)
    state = engine.classify(df)
    print(f"Detected Regime: {state['trend']} Core / {state['volatility']} Volatility")
    print(f"EMA 50: {state['ema50']:.2f} | EMA 200: {state['ema200']:.2f}")

def test_risk_management():
    print("\n--- Testing Risk Management (Dry Run) ---")
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    risk = RiskEngine(config)
    # Mocking a symbol info check (would fail without real MT5 connection)
    print("Risk Engine Initialized. Ready for dynamic lot sizing and Kill Switch verification.")

if __name__ == "__main__":
    test_indicators()
    test_regime_engine()
    test_risk_management()
    print("\n--- Local Logic Test Complete ---")
    print("Next Step: Update .env and run 'python main.py' for real-time MT5 testing.")
