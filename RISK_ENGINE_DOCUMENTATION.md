# 🛡️ V7.1 Risk Engine Documentation

The Risk Engine (`src/core/risk_manager.py`) is the core safety layer of the trading system. It handles adaptive lot sizing, portfolio heat management, and multi-phase circuit breakers based on a High-Water Mark (HWM) system.

## 1. Adaptive Lot Sizing Logic
The engine calculates lot sizes dynamically based on account equity and symbol volatility.

| Account Equity | Volatile Assets (BTC, Gold) | Standard Pairs (Forex) |
| :--- | :--- | :--- |
| **< $100** | 0.01 (Recovery Mode) | 0.01 (Recovery Mode) |
| **$100 - $200** | 0.01 | 0.03 |
| **$200 - $500** | 0.02 (Capped) | 0.03 |
| **> $500** | 0.02 (Capped) | 0.05 |

> [!IMPORTANT]
> **Drawdown Guard**: If Equity drops below 85% of Balance, the engine forces all new trades to **0.01 lots** regardless of other settings.

## 2. Portfolio Heat & Correlation
Before any trade is executed, the engine validates the total account "heat".

- **Max Portfolio Heat**: 15.0% (Total risk of all open positions).
- **Currency Basket Cap**: 10.0% (Max risk for a single base currency, e.g., all USD pairs).
- **Static Risk Assumption**: Each open trade is treated as **1.5% risk** for heat calculation purposes.

## 3. HWM Circuit Breakers (Protection Phases)
The engine tracks the **High-Water Mark (HWM)**—the highest equity reached during the session—and triggers halts based on drawdown from that peak.

### 🟡 Phase 1: Caution (11% HWM Drawdown)
- **Action**: Halt all new entries.
- **Duration**: 4-hour cooling-off period.
- **Trigger**: Equity drops 11% from its recent peak.

### 🟠 Phase 2: Emergency (23% HWM Drawdown)
- **Action**: **LIQUIDATE** all open positions + 24-hour halt.
- **Trigger**: Equity drops 23% from peak OR 23% from balance.
- **Note**: In *WAR ROOM* mode, this limit is extended to 50%.

### 🔴 Phase 3: Nuclear (40% Total Drawdown)
- **Action**: **HARD SHUTDOWN** of the entire bot loop.
- **Trigger**: 40% drawdown from balance.

## 4. Persistent State
Risk state (Peak Equity and Halt Timestamps) is saved to `config/risk_state_[login].json`. This ensures that even if the bot restarts, it remembers if it is currently in a "cooling-off" period or what its previous High-Water Mark was.

---

## Technical Implementation Details
- **Class**: `RiskEngine`
- **Primary Methods**:
    - `calculate_lot_size(symbol, risk_percent, stop_loss_points)`
    - `validate_portfolio_risk(symbol, risk_percent)`
    - `check_daily_stop()`: Returns `(is_halted, should_liquidate, is_hard_down)`
