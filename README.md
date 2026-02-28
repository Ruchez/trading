# Institutional Agentic Trading System V4

A professional, deterministic intraday trading system optimized for prop-firm funding and capital preservation.

## 🏗️ Project Structure
```text
Trading/
├── config/              # Configuration & Security (settings.json, security_vault.py)
├── docs/                # Comprehensive Manuals (Architecture, Strategy, Risk, Ops)
├── src/                 # Source Code
│   ├── bridge/          # MT5 Connection Layer (mt5_interface.py)
│   ├── core/            # Risk Managers, Portfolio, Validator
│   ├── comms/           # Telegram Services (Notifier, Command Service)
│   ├── strategies/      # Trading Logic (Intraday, Scalper)
│   ├── utils/           # Market Math, DB, Regime Engines
│   └── main_loop.py     # Execution Heart
├── launcher.py          # Entry Point
└── requirements.txt     # Dependencies
```

## 🚀 Quick Start
1.  Configure your credentials in `.env`.
2.  Adjust trading parameters in `config/settings.json`.
3.  Launch the system:
    ```powershell
    python launcher.py
    ```

## 📚 Documentation
For detailed technical information, architecture, and operational procedures, please refer to the comprehensive system manual:
- [System Manual](SYSTEM_MANUAL.md)

---
*Disclaimer: Trading involves risk. Use this system at your own discretion. Optimized for deterministic execution.*
