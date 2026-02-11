import json
import os
from datetime import datetime

class PatternMemory:
    """
    Stores snapshots of market conditions at the time of a trade.
    Used for later analysis to 'learn' which patterns work.
    """
    def __init__(self, storage_path="logs/pattern_memory.json"):
        self.storage_path = storage_path
        self._ensure_storage()
        
    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w') as f:
                json.dump([], f)

    def record_snapshot(self, symbol, signal_type, indicators, regime):
        """
        Saves a snapshot of the market state.
        Indicators should be a dict of values (RSI, Z-Score, etc.)
        """
        snapshot = {
            "id": f"{symbol}_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "signal": signal_type,
            "regime": regime,
            "indicators": indicators,
            "outcome": None # To be updated after trade close
        }
        
        with open(self.storage_path, 'r+') as f:
            data = json.load(f)
            data.append(snapshot)
            f.seek(0)
            json.dump(data, f, indent=4)
            
        return snapshot["id"]

    def update_outcome(self, snapshot_id, profit):
        """
        Updates the success/failure of a recorded pattern.
        """
        with open(self.storage_path, 'r+') as f:
            data = json.load(f)
            for snapshot in data:
                if snapshot["id"] == snapshot_id:
                    snapshot["outcome"] = "WIN" if profit > 0 else "LOSS"
                    snapshot["profit"] = profit
                    break
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    def get_winning_patterns(self, min_win_rate=0.7):
        """
        Analyzes memory to find high-probability setups.
        """
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
            
        if not data:
            return {}
            
        # Group by regime and signal type
        analysis = {}
        for s in data:
            if s["outcome"] is None: continue
            
            key = f"{s['regime']['trend']}_{s['signal']}"
            if key not in analysis:
                analysis[key] = {"wins": 0, "total": 0}
            
            analysis[key]["total"] += 1
            if s["outcome"] == "WIN":
                analysis[key]["wins"] += 1
        
        # Filter for high probability
        rankings = {}
        for key, stats in analysis.items():
            win_rate = stats["wins"] / stats["total"]
            if win_rate >= min_win_rate and stats["total"] > 5:
                rankings[key] = win_rate
                
        return rankings
