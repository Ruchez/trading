import json
import os
import requests
from typing import List, Dict

class AI_LearningEngine:
    """
    Processes trade snapshots and uses AI to identify strategy patterns and suggest refinements.
    """
    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv("GROK_API_KEY") or config.get("api_keys", {}).get("grok")
        self.api_url = "https://api.x.ai/v1/chat/completions" # Default Grok endpoint

    def analyze_trades(self, trade_data_path: str):
        """
        Loads trade data, batches it, and sends it to the AI for pattern analysis.
        """
        if not os.path.exists(trade_data_path):
            return "❌ No backtest data found to analyze."

        try:
            with open(trade_data_path, 'r') as f:
                trades = json.load(f)
        except Exception as e:
            return f"❌ Failed to load trade data: {e}"

        if not trades:
            return "📭 No trades recorded in the last session."

        # Separate wins and losses
        wins = [t for t in trades if t.get('outcome', {}).get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('outcome', {}).get('pnl', 0) <= 0]

        # Prepare a concise summary for the AI
        summary = self._prepare_summary(wins, losses)
        
        print(f"🧠 Sending {len(trades)} trades to AI for strategy post-mortem...")
        
        analysis = self._query_ai(summary)
        return analysis

    def _prepare_summary(self, wins, losses):
        """
        Distills raw trade data into a readable summary for the AI.
        """
        summary_text = "BACKTEST PERFORMANCE SUMMARY:\n"
        summary_text += f"Total Wins: {len(wins)}\n"
        summary_text += f"Total Losses: {len(losses)}\n\n"
        
        summary_text += "WINNING PATTERNS (Sample snapshots):\n"
        for i, t in enumerate(wins[:10]):
            summary_text += f"- Win {i+1}: {t['indicators']}\n"
            
        summary_text += "\nLOSING PATTERNS (Sample snapshots):\n"
        for i, t in enumerate(losses[:10]):
            summary_text += f"- Loss {i+1}: {t['indicators']}\n"
            
        return summary_text

    def _query_ai(self, summary):
        """
        Sends the distilled data to Grok/Gemini with a specific strategy-refinement prompt.
        """
        prompt = f"""
        You are an institutional trading consultant. Analyze the following backtest data for an 
        Institutional V5 Strategy (EMA Pullbacks, Liquidity Sweeps, VWAP Reversion).
        
        {summary}
        
        TASK:
        1. Identify the 3 most common technical reasons for LOSING trades.
        2. Identify the 1 common factor in the BIGGEST WINNING trades.
        3. Suggest 3 specific "Gated Filters" to enhance the strategy (ex: 'Only take XAUUSD longs if RSI < 65').
        4. Focus on STRATEGY logic (indicators, confluence), not risk management.
        
        Format your response in markdown for a professional technical manual.
        """

        if not self.api_key:
            return "⚠️ No API Key found. Please set GROK_API_KEY in .env."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "grok-beta", # Or preferred model
            "messages": [
                {"role": "system", "content": "You are an expert quantitative trading strategist."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"❌ AI Query Failed: {e}"
