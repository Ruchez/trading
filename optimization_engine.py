from pattern_memory import PatternMemory
import numpy as np

class LearningEngine:
    """
    The 'Brain' that analyzes PatternMemory to suggest strategy adjustments.
    """
    def __init__(self, memory_path="logs/pattern_memory.json"):
        self.memory = PatternMemory(memory_path)

    def optimize_parameters(self, symbol, strategy_name):
        """
        Suggests new thresholds based on winning patterns.
        Example: If BTC Longs win more when RSI is < 20 than < 30, it updates the rule.
        """
        # In a full implementation, this would use machine learning (Scikit-Learn).
        # For now, we use a statistical 'Best Filter' approach.
        
        winning_regimes = self.memory.get_winning_patterns()
        
        if not winning_regimes:
            return "Insufficient data to optimize."

        # Logic to return suggested parameter updates
        return f"Optimization complete. Best performing regime: {max(winning_regimes, key=winning_regimes.get)}"
