from src.strategies.institutional_v5 import InstitutionalStrategyV5
from src.strategies.war_room import WarRoomGoldStrategy

STRATEGY_MAP = {
    "v5": InstitutionalStrategyV5,
    "institutional_v5": InstitutionalStrategyV5,
    "war_room": WarRoomGoldStrategy
}

def get_strategy(strategy_name, symbol, config):
    """
    Factory function to return a strategy instance based on name.
    """
    strategy_class = STRATEGY_MAP.get(strategy_name.lower(), InstitutionalStrategyV5)
    return strategy_class(symbol, config)
