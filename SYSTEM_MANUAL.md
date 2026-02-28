# Institutional Agentic Trading System - V5 Manual

## 📌 Executive Summary
The Institutional Agentic Trading System (V5) is a state-of-the-art, asynchronous trading engine designed for professional intraday execution. Evolving from the V4 framework, V5 shifts the philosophy from "Frequency" to "Precision," operating under a strict "Quality over Quantity" mandate. The system is optimized for prop-firm compliance (e.g., FTMO, MyForexFunds, Rocket21) and high-equity retail accounts, focusing on capital preservation through advanced multi-timeframe confluence and AI-augmented sentiment analysis. Unlike traditional retail bots that chase every move, V5 behaves like a mathematical risk manager, prioritizing the avoidance of "noise" trades in favor of high-conviction institutional setups. Every parameter in the V5 build is tuned for deterministic performance, ensuring that the bot remains emotionless during high-volatility sessions.

## 🏗️ System Architecture (V5 Evolution)
The core architecture remains an asynchronous multi-loop engine powered by Python's `asyncio`. This ensures non-blocking execution where risk monitoring and trade execution operate in parallel, eliminating the "lag" often associated with sequential scripts. By leveraging async processing, V5 can monitor multiple symbols across multiple timeframes without missing a single tick of price action.

### 1. Risk Monitor Loop (100ms Heartbeat)
The "Safety Net" of the system. It monitors account health every 100 milliseconds, independent of the trading logic.
- **HWM Circuit Breakers**: Tracks High-Water Mark (peak equity) to trigger phased shutdowns based on drawdown. This ensures that the system locks in profits and defends against catastrophic equity curve decay. The HWM is updated only when equity reaches a new peak, creating a "sliding roof" of protection.
- **Immediate Liquidation**: In the event of an "Emergency" drawdown (23%), the loop sends emergency close signals to MT5. This bypasses the standard execution logic to ensure capital is protected at all costs. The liquidation is executed via a multi-threaded burst to minimize slippage.
- **Exposure Guard**: Monitors total account heat (cumulative risk). If the cumulative risk of all open positions exceeds the configured limit (12% by default), any new entry signals detected by the execution loop are instantly suppressed. It also enforces "Currency Basket" limits to prevent over-exposure to a single currency (e.g., USD).

### 2. Execution Loop (1s Heartbeat)
The "Brain" of the system. In V5, this loop is significantly more selective, focusing on higher-timeframe triggers.
- **Focused Symbol Scanning**: Restricted to high-liquidity pairs (XAUUSD, BTCUSD, EURUSD, USDJPY, AUDUSD). This specialization allows for more accurate indicator calibration and reduced spread impact.
- **Multi-TF Data Ingestion**: Concurrently processes H4, H1, M15, M5, and M1 data. This hierarchical approach prevents "counter-trend" trading, ensuring M5 triggers align with the H4 macro bias. The system uses a "Look-Back" buffer of 100-300 bars per timeframe to ensure indicator stability.
- **Volatility Gating**: Uses ATR-based thresholds on the M1 timeframe. If market participation is too low (e.g., during Asian session consolidation), the execution loop enters a "Sleep" state for that symbol to avoid commission-heavy chop. V5 uses adaptive volatility gates that widen during news events to prevent "stop-hunting."

### 3. Trade Manager (New in V5)
A standalone component dedicated to active position management. Most retail bots set SL/TP and forget; V5 actively "manages" the trade once it is live.
- **Dynamic Trailing**: Implements R-multiple based trailing stops. When a trade hits 1.0R (profit equals initial risk), the SL is moved to Break-Even + 5 pips. At 1.5R, the system begins trailing using a 1.2x ATR buffer, locking in the majority of the move while giving the price room to breathe.
- **Early Exit Engine**: Monitors for regime shifts. If a trade was entered during a "Trending" regime but the Market Regime Engine detects a shift to "Choppy" or "Volatile Reversal," the Trade Manager can close the position early. This "Momentum Fade" detection uses RSI divergence and ADX slope analysis on the M5 timeframe.

## ⚡ Institutional V5 Strategy Suite
The V5 strategy suite moves away from isolated indicators towards a comprehensive **Confluence Scoring System (CSS)**. A trade is only executed if it achieves a minimum score of 3 points (max 5).

### 1. Multi-TF Trend Alignment (The H4 Filter)
Every trend-based setup must align with the H4 and H1 EMA structures.
- **Logic**: H4 EMA50 > H4 EMA200 (Primary Bullish Bias).
- **Alignment**: H1 Close must be above H4 EMA50.
- **Result**: If H4 is bullish and H1 is bullish, the system only looks for BUY setups. This "Hard Filter" eliminates roughly 60% of low-probability trades that fail due to macro-trend disagreement.

### 2. High-Probability Sub-Strategies
- **Institutional Pullback (3-5pt)**:
    - **Step 1**: Identify H4/H1 trend bias.
    - **Step 2**: Wait for M15 pullback to the EMA20 ribbon (the "Value Area").
    - **Step 3**: Confirm price is in a Fibonacci Golden Zone (0.5 - 0.618).
    - **Step 4**: Execute on M5 rejection wick (Pin Bar) with a volume spike. Volume must be at least 1.5x the 20-bar average.
    - **Score**: 1 for Trend, 1 for Pullback, 1 for Fib, 1 for Wick, 1 for Vol.
- **Liquidity Sweep (4-5pt)**: Detects institutional stop-runs on M15 levels. It requires price to spike below a previous 30-candle low then close back above it within 2 bars. This must be confirmed by a "Displacement Candle" (a body size 1.5x larger than the 20-bar average). This is the hallmark of "Smart Money" entering the market.
- **VWAP Max-Sigma Reversion**: Only triggers at 3.0 standard deviations from the daily VWAP in "Ranging" regimes. It targets the "Reversion to Mean" (the VWAP line). This serves as a "Pressure Valve" for the system, capturing overextended moves when the market is exhausted.
- **Bollinger + Keltner Squeeze**: Detects periods of extreme low volatility where the Bollinger Bands contract inside the Keltner Channels. V5 waits for the "Squeeze Release"—a breakout confirmed by an ADX spike (>25) and a volume surge.

### 3. AI Sentiment Boost (Grok Integration)
The system optionally queries the Grok API (xAI) for a global sentiment check.
- **Function**: Sentiment "Bullish" = +1 point. Sentiment "Bearish" = -1 point.
- **Value**: This provides a "Macro Overlay" that standard technical indicators cannot capture. For example, if technicals are bullish but the Grok-AI reports an emergency interest rate hike or black-swan macro news, the sentiment boost will cancel the trade or prevent the confluence score from reaching the entry threshold.

## 🛡️ Institutional Survival Protocol (Risk V5)
Risk management is not an afterthought in V5; it is the core feature.

### 1. Phased Circuit Breakers (Tightened)
- **Phase 1: Caution (11% Drawdown from HWM)**: System halts all new entries for 4 hours. Existing trades are shifted to "Aggressive Management" (trailing SL moved closer). This prevents "drawdown digging" where a trader tries to trade their way out of a loss.
- **Phase 2: Emergency (23% Drawdown from HWM)**: System liquidates all open positions and enters a 24-hour "Nuclear Lockdown." This phase is designed to stop a "trading tilt" or a black-swan event from blowing an account. 23% is the hard ceiling, ensuring compliance with most prop-firm "Max Drawdown" rules.

### 3. Recovery Mode & Lot Sizing
- **Recovery Mode**: If equity falls below $100, the system forces 0.01 lot sizes regardless of strategy settings. This "Protective Buffer" ensures the account stays alive during a drawdown streak. It effectively turns the system into a "Penny Stock" engine until it climbs back into the safe equity zone.
- **Institutional Sizing**: For accounts above $100, the system uses a starting base of 0.03 lots. It then applies volatility scaling: if ATR is high, lot size is reduced (wider stops); if ATR is low, lot size is increased (normalized risk).
- **Equity Curve Filter**: If the system records 3 consecutive losses across all symbols, it enters a forced 2-hour "Reflection Mode" to wait for a market regime shift. This stops the "Death by a Thousand Cuts" during choppy, non-trending markets.

### 4. Correlated Pair Avoidance
The system prevents "Double Exposure" by detecting correlated pairs (e.g., AUDUSD and GBPUSD). If a SELL is already open on AUDUSD, the system will reject a SELL signal on GBPUSD. This ensures that the system doesn't accidentally bet 3% of the account on "USD Strength" across multiple pairs, which would be a catastrophic risk if the USD suddenly weakened.

## 📊 Performance & Logging
Every action the bot takes is logged for later analysis:
- **thinking.log**: A granular look into the bot's "Decision Tree." It shows every signal scanned, why it was rejected (e.g., "Score: 2/3: Missing Fib Confluence"), and the exact price levels detected.
- **trade_logs.db** (SQLite): A permanent record of all trades. This data is used by the `/learn` command to generate AI-driven post-mortem reports.

## 📜 Technical Implementation Details
- **Indicator Pipeline**: All indicators (ATR, RSI, VWAP, ADX, Fibonacci) are calculated locally using `pandas` (vectorized operations) and `numpy`. We avoid MT5's built-in indicators to ensure that the bot sees the exact same numbers regardless of broker terminal variations.
- **Market Regime Engine**: A dedicated utility class that classifies market states as 'TRENDING', 'RANGING', or 'VOLATILE'. Each strategy is "Regime Locked"—for example, Trend Continuation is disabled in Ranging markets.

---
*Disclaimer: Trading involves significant risk. The V5 Institutional System is a tool for professional traders and does not guarantee profit. Developed for deterministic, low-latency execution and capital preservation. Optimized for Exness Zero/Raw accounts.*
