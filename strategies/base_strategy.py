import abc
from datetime import datetime

class BaseStrategy(abc.ABC):
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.config = config
        self.last_signal_time = None
        self.last_trade_time = 0 # Unix timestamp of last entry/exit
        self.cooldown_minutes = config.get('risk_management', {}).get('cooldown_period_minutes', 30)
        self.latest_indicators = {} # To be populated by children for learning

    @abc.abstractmethod
    def check_signal(self, data):
        """
        Check for entry signals based on the data.
        Returns 'BUY', 'SELL', or None.
        """
        pass

    @abc.abstractmethod
    def check_exit(self, position, data):
        """
        Check for exit signals for an open position.
        Returns True if the position should be closed, False otherwise.
        """
        pass

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{self.symbol}] {message}")
