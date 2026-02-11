# Institutional AI Trading System: Comprehensive Technical Documentation

**Version:** 2.0  
**Date:** October 2026  
**Target Audience:** System Architects, algo-traders, and Maintainers.

---

## 1. Executive Summary & Framework Definition

This document serves as the authoritative technical reference for the **Agentic AI Trading System**. The system represents a paradigm shift from traditional algorithmic trading by integrating a **Large Language Model (LLM)**—specifically **Grok-3**—directly into the decision-making loop.

### 1.1 The Framework: Hybrid Cognitive Architecture
The user might ask: *"What framework is this?"*
It is not a standard web framework like Django. It is a custom **Event-Driven Cognitive Framework** composed of three distinct layers:
1.  **The Reptilian Brain (Execution Layer)**: Python scripts (`mt5_bridge.py`, `risk_engine.py`) handling high-frequency execution, connection to the simple MetaTrader 5 terminal, and strict risk checks. It is fast, deterministic, and "dumb".
2.  **The Cortex (Cognitive Layer)**: The `AIBrain` module interfaces with Grok-3. It provides semantic understanding, regime classification, and "gut checks" on trades.
3.  **The Event Loop**: The `main.py` core which orchestrates the synchronous data flow between the Market, the math (Strategies), and the AI.

---

## 2. System Architecture

The codebase handles the complex orchestration of asynchronous data streams through a synchronous Event-Loop architecture.

### 2.1. High-Level Logic Flow

The system operates on an infinite `while True` loop (`main.py`) that executes the following cycle approximately every 1-2 seconds:

1.  **State Synchronization**: Checks connection status with `MT5Bridge` and syncs with the Telegram Command Queue.
2.  **Risk Audit**: The `RiskEngine` calculates real-time equity drawdown. If the **Daily Loss Limit (20%)** is breached, a `Force Liquidation` event closes all positions and halts the bot.
3.  **Active Position Management**:
    *   **Scalping Logic**: checks for fixed profit targets.
    *   **Dynamic Break-Even**: Calculates **ATR (Volatility)**. If price moves `1.5x ATR` in profit, SL is moved to `Entry + 5 points`. This adapts to both Gold (high volatility) and Euro (low volatility).
    *   **AI Review**: Periodically queries the AI: *"Given the current price action, should I hold, exit, or tighten stops?"*
    *   **AI Review**: Periodically (every 3-10 minutes) takes a "Market Snapshot" and queries the AI: *"Given the current price action, should I hold, exit, or tighten stops?"*
4.  **Signal Generation**:
    *   Iterates through all enabled symbols in `config.json`.
    *   Fetches M1, M15, and H4 dataframes.
    *   Passes data to the assigned `Strategy` (e.g., `ScalpStrategy`).
    *   If a preliminary `BUY` or `SELL` signal is generated, it initiates the **AI Validation Handshake**.
5.  **Cognitive Validation**:
    *   The `AIBrain` receives the technical data + a calculated "Narrative" (e.g., *"Trend is bullish but RSI is overbought"*).
    *   It references its **Long-Term Memory** (`lessons_learned.json`) to see if it has made similar mistakes recently.
    *   It returns a JSON decision: `PROCEED` or `SKIP`, along with a `Conviction Score` (0-100).
6.  **Execution**:
    *   If Conviction > 60%, the `RiskEngine` calculates the allowable lot size.
    *   The `MT5Bridge` routes the order to the exchange with calculated Stop Loss (SL) and Take Profit (TP).

---

## 3. Core Component Analysis

### 3.1. The Cognitive Layer: `AIBrain` (`ai_brain.py`)
This module is the differentiator. It abstracts the complexity of LLM interaction into a simple API for the trading loop.

*   **Prompt Engineering**: The system uses dynamically constructed System Prompts.
    *   **Scalper Persona**: *"You are an Aggressive Scalper. Focus on momentum and immediate flow. Output JSON..."*
    *   **Intraday Persona**: *"You are a Senior Portfolio Manager. Focus on structure, support/resistance, and risk-reward. Output JSON..."*
*   **Structured Output**: The AI is forced to output valid JSON schemas. The code blindly parses this JSON to extract `action`, `sl`, `tp`, and `reasoning`.
*   **The Learning Loop**: This is the most advanced feature.
    *   When a trade hits its Stop Loss, the bot captures the *Entry Snapshot* and the *Exit Snapshot*.
    *   It asks the AI: *"Why did this trade fail?"*
    *   The AI might reply: *"Mistake: Counter-trend entry. Lesson: Don't buy breakouts below the 200 EMA."*
    *   This "Lesson" is saved to `lessons_learned.json`.
    *   **Critical**: In the *next* trade request, this lesson is injected into the prompt: *"Recent Lessons: Don't buy breakouts below the 200 EMA."* This prevents the bot from making the same mistake twice.

### 3.2. Due Diligence: `RegimeEngine` (`regime_engine.py`)
Strategies often fail because they run in the wrong market conditions (e.g., a trend-following strategy in a ranging market). The Regime Engine solves this by classifying the market state *before* a strategy is allowed to look for signals.

*   **Trend Classification**:
    *   Calculates 50-period and 200-period Exponential Moving Averages (EMA).
    *   **BULLISH**: Price > EMA50 > EMA200.
    *   **BEARISH**: Price < EMA50 < EMA200.
    *   **NEUTRAL**: EMAs are crossed or price is between them.
*   **Volatility Classification**:
    *   Uses **Average True Range (ATR)** and Normalized Range.
    *   **COMPRESSION**: Current ATR < 0.7 * Moving Average of ATR. (Indicates an explosive move is imminent).
    *   **EXPANSION**: Current ATR > 1.5 * Moving Average of ATR. (Indicates trend exhaustion or climax).

### 3.3. Execution & Connectivity: `MT5Bridge` (`execution/mt5_bridge.py`)
Directly interfering with the MetaTrader 5 terminal is prone to errors. This class handles the "dirty work" of API communication.

*   **Smart Reconnection**: If the terminal disconnects (common on weak VPS), the bridge attempts to re-initialize the terminal up to 3 times with exponential backoff.
*   **Order Normalization**:
    *   **Digits**: MT5 requires prices to be rounded to the exact number of decimal places for the symbol (e.g., 2 for JPY pairs, 5 for EURUSD). The bridge handles this automatically via `symbol_info.digits`.
    *   **Filling Modes**: Different brokers support different filling policies (Fill-or-Kill, Immediate-or-Cancel). The bridge dynamically detects the allowed mode for the symbol to prevent `Unsupported Filling Mode` errors.
    *   **Slippage Control**: Sets a `deviation` parameter (default 20 points) to allow for minor price execution variance during high volatility.

### 3.4. Capital Protection: `RiskEngine` (`risk_engine.py`)
The Guardian of the account. It cannot be overridden by the AI.

*   **Logic**:
    *   **Gold (XAUUSD)**: Hard-coded safety limits. Max 0.02 lots. Max 2 concurrent positions. Gold is volatile and dangerous; the engine respects that.
    *   **Currencies**: Dynamic scaling. Uses a `Balance / 1000 * 0.1` formula to determine lot size.
*   **Daily Circuit Breaker**:
    *   On every loop, it checks `(Balance - Equity) / Balance`.
    *   If drawdown > **20%**, it triggers `check_daily_stop() -> True`.
    *   This results in immediate liquidation of all positions and a cessation of trading for the day.

### 3.5. Remote Command: `TelegramCommander` (`telegram_commander.py`)
Allows the operator to control the bot from a mobile device.

*   **Security**: It only accepts commands from `authorized_ids` defined in the Vault. It ignores all other messages.
*   **Command Set**:
    *   `/status`: Returns PnL, Open Positions breakdown, and current mode.
    *   `/panic`: **EMERGENCY ACTION**. Closes every single open position immediately. Used during Flash Crashes.
    *   `/stop`: Pauses signal generation. Open positions remain open but are monitored.
    *   `/resume`: Re-enables signal generation.

---

## 4. Operational Guide

### 4.1. Installation & Setup

1.  **Prerequisites**:
    *   Windows OS (MT5 requirement).
    *   Python 3.10+.
    *   MetaTrader 5 Terminal installed and logged in to your broker account.

2.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```ini
    MT5_LOGIN=2001830172
    MT5_PASSWORD=********
    MT5_SERVER=JustMarkets-Demo
    
    GROK_API_KEY=xai-...
    
    TELEGRAM_BOT_TOKEN=123:ABC...
    TELEGRAM_CHAT_ID=987654321
    ```

3.  **Configuration**:
    Edit `config.json` to define your traded pairs (Ensure suffixes like `.m` are correct):
    ```json
    "symbols": {
        "XAUUSD.m": { "enabled": true, "strategies": ["scalp"] },
        "EURUSD.m": { "enabled": true, "strategies": ["breakout"] }
    }
    ```

4.  **Execution**:
    Run the bot from the command line:
    ```bash
    python main.py
    ```
    *Output*: You should see "Connected to MT5", followed by "Thinking Agent Started".

### 4.2. Strategy Development Guide

To add a new strategy (e.g., "RSI Reversal"), follow this pattern:

1.  Create `strategies/rsi_reversal.py`.
2.  Inherit from `BaseStrategy`.
3.  Implement `check_signal(self, data)`:
    ```python
    from strategies.base_strategy import BaseStrategy

    class RSIReversalStrategy(BaseStrategy):
        def check_signal(self, data):
            # 1. Calc RSI
            rsi = calculate_rsi(data, 14)
            
            # 2. Logic
            if rsi < 30: return 'BUY'
            if rsi > 70: return 'SELL'
            
            return None
    ```
4.  Register the strategy in `main.py` inside the strategy initialization loop.

---

## 5. Troubleshooting & Maintenance

### Common Errors

1.  **"IPC Timeout" / "Terminal Initialization Failed"**:
    *   *Cause*: MT5 execution is blocked or the terminal is hung.
    *   *Fix*: Kill the `terminal64.exe` process in Task Manager and restart `main.py`. The bridge will auto-restart the terminal.

2.  **"Market Closed"**:
    *   *Cause*: Trying to trade Crypto on a Forex-only broker during weekends, or Forex during weekends.
    *   *Fix*: The `is_market_open()` check in `mt5_bridge` handles this, but ensure your computer clock is synced.

3.  **"Invalid Stops" (Retcode 10016)**:
    *   *Cause*: SL/TP is too close to the current price (within the broker's "Stops Level").
    *   *Fix*: The code automatically checks `symbol_info.trade_stops_level` and adds a 5-point buffer. If this persists, increase the buffer in `mt5_bridge.py`.

4.  **"Authorization Failed"**:
    *   *Cause*: Wrong Password or Server in `.env`.
    *   *Fix*: Double-check the `MT5_SERVER` name exactly as it appears in the terminal login box (case sensitive).

---

## 6. Security Protocol (`security_vault.py`)

Security is paramount when handling live funds.
*   **Credential Isolation**: No passwords are hardcoded. They are loaded strictly from environment variables via `python-dotenv`.
*   **Scope Isolation**: The Telegram Bot checks the `User ID` of the sender. If a random user finds your bot handle and sends `/panic`, the bot ignores it and logs a security warning.

---

## 7. Conclusion

This documentation confirms the integrity and sophistication of the deployed system. It is not merely a script but a fully fledged **Trading Application**. The integration of Grok-3 provides a competitive edge by allowing the system to adapt to changing market conditions in a way that static algorithms cannot.

The system is currently in **Active Deployment** state, ready for live market operations pending user confirmation of the `.env` credentials.
