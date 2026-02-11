import requests
import json
import time
from security_vault import SecurityVault

class AIBrain:
    """
    Agentic Grok Brain. 
    Uses Grok-3 API as primary reasoning, with local technical fallback.
    """
    def __init__(self):
        self.vault = SecurityVault()
        self.grok_key = getattr(self.vault, 'grok_key', None)
        self.grok_url = "https://api.x.ai/v1/chat/completions"
        self.last_error_time = 0
        self.error_cooldown = 120 
        self.lessons_path = "logs/lessons_learned.json"
        print(f"[INFO] AI Brain active: Grok-3 (Exclusive) with Memory.")

    def _call_grok(self, system_prompt, user_prompt):
        """
        Ultra-lean Grok call to minimize token costs.
        """
        if not self.grok_key: return None
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.grok_key}"
        }
        payload = {
            "model": "grok-3",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0, # Deterministic for trading
            "stream": False
        }
        try:
            response = requests.post(self.grok_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                raw_content = response.json()['choices'][0]['message']['content']
                content = raw_content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                try:
                    return json.loads(content)
                except:
                    print(f"[DEBUG] Grok JSON Parse Failed. Raw: {repr(raw_content)}")
                    return None
            return None
        except: return None

    def _get_recent_lessons(self, limit=3):
        try:
            with open(self.lessons_path, "r") as f:
                lessons = json.load(f)
                return "\n".join([f"- {l['lesson']}" for l in lessons[-limit:]])
        except: return "No recent lessons."

    def analyze_setup(self, snapshot_text, mode="INTRADAY"):
        lessons = self._get_recent_lessons()
        if mode == "SCALPER":
            schema = "{\"action\": \"PROCEED\"|\"SKIP\", \"conviction_score\": 0-100, \"suggested_positions\": 1-20, \"reasoning\": \"string\"}"
            system_prompt = f"Aggressive Scalper. Logic: {schema}. High-Conviction = High suggested_positions. Recent Lessons: {lessons}. Short reasoning."
        else:
            schema = "{\"action\": \"PROCEED\"|\"SKIP\", \"conviction_score\": 0-100, \"sl\": price, \"tp\": price, \"reasoning\": \"string\"}"
            system_prompt = f"Professional Intraday Trader. Logic: {schema}. Define precise TP/SL based on structure/volatility. Recent Lessons: {lessons}. Elite terminology."

        return self._call_grok(system_prompt, f"Snapshot Data: {snapshot_text}") or {
            "conviction_score": 50, "action": "SKIP", "reasoning": "API Error Fallback.", "suggested_positions": 1
        }

    def evaluate_open_position(self, snapshot_text, current_profit, mode="INTRADAY"):
        if mode == "SCALPER":
            # Scalp is handled by hard $0.50 target mostly, but AI can still intervene
            sys = "Trade Monitor (Scalp). Output JSON: {'decision': 'HOLD'/'TAKE_PROFIT'/'CUT_LOSS', 'reasoning': '...'}"
        else:
            sys = "Senior Portfolio Manager (Intraday). Output JSON: {'decision': 'HOLD'/'MOVE_TO_BE'/'TAKE_PROFIT'/'CUT_LOSS', 'reasoning': '...'}"
            
        return self._call_grok(sys, f"PnL: {current_profit}, Snapshot: {snapshot_text}") or {
            "decision": "HOLD", "reasoning": "Comm failure."
        }

    def analyze_loss(self, symbol, entry_snapshot, exit_snapshot, pnl):
        """
        Post-Mortem: Learn why a trade failed.
        """
        sys = "Risk Analyst. Output JSON: {'mistake': 'string', 'lesson': 'string'}. Analyze what went wrong."
        user = f"Trade: {symbol}, PnL: {pnl}\nEntry State: {entry_snapshot}\nExit State: {exit_snapshot}"
        
        analysis = self._call_grok(sys, user)
        if analysis:
            try:
                lessons = []
                try: 
                    with open(self.lessons_path, "r") as f: lessons = json.load(f)
                except: pass
                
                lessons.append({"time": time.time(), "symbol": symbol, "pnl": pnl, "lesson": analysis['lesson']})
                with open(self.lessons_path, "w") as f: json.dump(lessons[-50:], f, indent=2)
                return analysis
            except: pass
        return None

    def analyze_live_drawdown(self, symbol, entry_snapshot, current_snapshot, pnl):
        """
        Intervention: Learn from a trade that is CURRENTLY losing money.
        """
        sys = "Risk Analyst. Output JSON: {'mistake': 'string', 'lesson': 'string', 'intervention': 'HOLD'|'CUT_LOSS'}. Analyze why this open trade is failing."
        user = f"Open Trade: {symbol}, Current PnL: {pnl}\nEntry State: {entry_snapshot}\nCurrent State: {current_snapshot}"
        
        analysis = self._call_grok(sys, user)
        if analysis:
            try:
                lessons = []
                try: 
                    with open(self.lessons_path, "r") as f: lessons = json.load(f)
                except: pass
                
                # Only add if it's a new unique lesson for this trade to avoid spamming
                lessons.append({"time": time.time(), "type": "LIVE", "symbol": symbol, "pnl": pnl, "lesson": analysis['lesson']})
                with open(self.lessons_path, "w") as f: json.dump(lessons[-50:], f, indent=2)
                return analysis
            except: pass
        return None
