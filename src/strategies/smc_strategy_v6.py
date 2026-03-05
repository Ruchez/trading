import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy
from src.utils.market_math import (
    determine_trend, detect_fvg, detect_order_blocks,
    detect_liquidity_sweep, detect_structure_break,
    calculate_atr, has_rejection_wick,
    is_overlap_session, is_low_volatility
)

class SMCStrategyV6(BaseStrategy):
    """
    SMC Strategy V6 - "Next Gen Rule-Based Execution"
    Strict multi-timeframe Smart Money Concepts.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.name = "SMC_V6_RULES"
        self.min_confluence_score = 3
        self.last_sweep_time = None # Track the time of the last processed sweep

    def check_signal(self, mtf_data, sentiment_boost=0, regime='NEUTRAL'):
        """
        Processes multi-TF data using strict SMC rules.
        A. Bias (Daily/4H) -> B. Preparation (1H/15M) -> C. Entry (5M/1M)
        """
        # Timeframe extraction
        d1  = mtf_data.get('D1', pd.DataFrame())
        h4  = mtf_data.get('H4', pd.DataFrame())
        h1  = mtf_data.get('H1', pd.DataFrame())
        m15 = mtf_data.get('M15', pd.DataFrame())
        m5  = mtf_data.get('M5', pd.DataFrame())
        m1  = mtf_data.get('M1', pd.DataFrame())

        if h4.empty or m15.empty or m5.empty:
            return None, 0, "Wait (Missing TF Data)"

        # --- SESSION & VOLATILITY FILTERS ---
        is_high_liquidity = is_overlap_session()
        slow_market = is_low_volatility(m15)

        # --- STEP A: Market Context (HTF Filter) ---
        bias_tf = h4 # Using H4 as primary HTF bias
        trend = determine_trend(bias_tf)
        
        if trend == 'SIDEWAYS':
            return None, "Wait (HTF Sideaways/Chop)"

        # Mark HTF Zones (FVGs, OBs)
        htf_fvgs = detect_fvg(bias_tf)
        htf_obs = detect_order_blocks(bias_tf)
        
        bias = 'BUY' if trend == 'UPTREND' else 'SELL'
        
        # --- STEP B: Preparation (Mid-TF Confirmation) ---
        # 1H/15M Liquidity Sweep + Structure Break
        prep_tf = m15
        sweep_info = detect_liquidity_sweep(prep_tf, window=40)
        bos_choch = detect_structure_break(prep_tf)
        
        sweep = sweep_info is not None
        valid_prep = False
        prep_reason = "No Prep"
        
        # Rule: Liquidity Sweep + Break in trend direction
        if sweep:
            sweep_type = 'BULLISH' if 'BULLISH' in sweep_info['type'] else 'BEARISH'
            if (bias == 'BUY' and sweep_type == 'BULLISH') or (bias == 'SELL' and sweep_type == 'BEARISH'):
                if bos_choch:
                    valid_prep = True
                    prep_reason = f"Confirmed {sweep_type} Sweep + BoS"
        
        if not valid_prep:
            return None, f"Wait ({prep_reason} on M15)"

        # --- STEP C: Entry (LTF Precision) ---
        # 5M/1M Entry Zones
        entry_tf = m5
        current_price = entry_tf['close'].iloc[-1]
        
        # Calculate Conviction Score based on Confluence
        # 1 point if Bias is strong (not mixed)
        # 1 point if Sweep is confirmed
        # 1 point if BoS/CHoCH is confirmed
        # 2 points if entry is inside HTF FVG or OB
        conviction = 1
        if sweep: conviction += 1
        if bos_choch: conviction += 1
        
        in_zone = False
        zone_type = ""
        
        # 1. FVG Retrace Entry check
        for fvg in htf_fvgs:
            if fvg['bottom'] <= current_price <= fvg['top'] and fvg['type'] == ('BULLISH' if bias == 'BUY' else 'BEARISH'):
                in_zone = True
                zone_type = "FVG"
                break

        # 2. OB Retest Entry check
        if not in_zone:
            for ob in htf_obs:
                if ob['bottom'] <= current_price <= ob['top'] and ob['type'] == ('BULLISH' if bias == 'BUY' else 'BEARISH'):
                    in_zone = True
                    zone_type = "OB"
                    break
                    
        if in_zone: conviction += 2

        # Final Entry Execution Rules
        if in_zone and has_rejection_wick(entry_tf, bias, 0.4):
            # One entry per sweep rule
            sweep_time = sweep_info['time'] if isinstance(sweep_info, dict) else "unknown"
            if sweep_time == self.last_sweep_time and sweep_time != "unknown":
                return None, 0, f"Wait (Already entered on this sweep: {sweep_time})"
            
            # Session/Volatility Final Check
            if not is_high_liquidity and not (slow_market and conviction >= 5):
                if slow_market:
                    return None, 0, f"Wait (Low Volatility/{conviction} conviction too low to trade slow move)"
                return None, 0, "Wait (Outside London/NY Overlap)"

            self.last_sweep_time = sweep_time
            return bias, conviction, f"V6 SMC {bias}: {zone_type} Entry (Conviction {conviction}/5)"

        # 3. Liquidity Rack + Rejection (Alternative)
        if sweep and bos_choch and has_rejection_wick(entry_tf, bias, 0.5):
            sweep_time = sweep_info['time'] if isinstance(sweep_info, dict) else "unknown"
            if sweep_time == self.last_sweep_time and sweep_time != "unknown":
                return None, 0, f"Wait (Already entered on this sweep: {sweep_time})"

            if not is_high_liquidity and not (slow_market and conviction >= 5):
                return None, 0, "Wait (Outside high liquidity window)"

            self.last_sweep_time = sweep_time
            return bias, conviction, f"V6 SMC {bias}: Liquidity Rack (Conviction {conviction}/5)"

        return None, 0, f"Scanning (Bias {bias}, Prep OK, Conviction {conviction}/5, waiting for rejection)"

    def check_exit(self, position, mtf_data):
        """
        Structure-based exits handled by TradeManager.
        """
        return None
