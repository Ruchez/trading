# Multi-Instrument Trading Bot (Python + MT5)

This bot is a modular system for trading multiple instruments (Gold, BTC, Forex) with a focus on scalping and trend following.

## Folder Structure
- `strategies/`: Contains strategy logic (Base class + Scalp implementation).
- `execution/`: Contains the `MT5Bridge` for interacting with MetaTrader 5.
- `data/`: Storage for historical or tick data.
- `logs/`: Application logs.
- `config.json`: Central configuration file.
- `main.py`: Main entry point to run the bot.

## Setup
1. Open MetaTrader 5 and log into your account (Exness recommended).
2. Go to `Tools -> Options -> Expert Advisors` and enable "Allow Algorithmic Trading" and "Allow DLL imports".
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Update `config.json` with your account details (if not already logged in).
5. Run the bot:
   ```bash
   python main.py
   ```

## Scalping Strategy (implemented)
- **Timeframe**: M1
- **Logic**: Uses a combination of price breakouts and RSI momentum to catch quick moves.
- **Execution**: Sends immediate orders with fixed SL/TP via the Python API.
