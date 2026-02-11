import MetaTrader5 as mt5
import pandas as pd
import time
from security_vault import SecurityVault

class MT5Bridge:
    def __init__(self, config):
        self.config = config
        self.vault = SecurityVault()
        self.credentials = self.vault.get_credentials()
        
    def connect(self, retries=3):
        if not self.vault.validate():
            return False
            
        for attempt in range(retries):
            # Proactively shutdown any existing session
            mt5.shutdown()
            time.sleep(1)
            
            # 1. Initialize empty (using open terminal)
            if not mt5.initialize():
                print(f"MT5 terminal initialization failed. Error: {mt5.last_error()}")
                time.sleep(2 ** attempt)
                continue

            # 2. Perform Login
            print(f"Attempting login to {self.credentials['server']}...")
            success = mt5.login(
                login=self.credentials['login'], 
                password=self.credentials['password'], 
                server=self.credentials['server']
            )
            
            if success:
                print(f"Connected to Exness MT5 - Account: {mt5.account_info().login}")
                
                # Ensure all configured symbols are visible in Market Watch
                if 'symbols' in self.config:
                    for symbol in self.config['symbols'].keys():
                        if not mt5.symbol_select(symbol, True):
                            print(f"[WARNING] Failed to select {symbol} in Market Watch.")
                        else:
                            # Fresh tick request to "wake up" the symbol
                            mt5.symbol_info_tick(symbol)
                            
                return True
            else:
                print(f"Login attempt {attempt+1} failed. Error: {mt5.last_error()}")
                time.sleep(2 ** attempt)
        
        print(f"Failed to connect after {retries} attempts.")
        return False

    def get_data(self, symbol, timeframe, n=100):
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        if rates is None:
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_mtf_data(self, symbol):
        """
        Returns a dictionary of dataframes for different timeframes.
        """
        return {
            "M1": self.get_data(symbol, mt5.TIMEFRAME_M1, 250),
            "M15": self.get_data(symbol, mt5.TIMEFRAME_M15, 100),
            "H4": self.get_data(symbol, mt5.TIMEFRAME_H4, 50)
        }

    def get_filling_mode(self, symbol):
        """
        Detects the supported filling mode for the symbol.
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return mt5.ORDER_FILLING_FOK

        # Try to match the broker's allowed filling modes using standard MT5 bitmask
        # 1 = SYMBOL_FILLING_FOK, 2 = SYMBOL_FILLING_IOC
        filling_type = symbol_info.filling_mode
        if filling_type & 1:
            return mt5.ORDER_FILLING_FOK
        elif filling_type & 2:
            return mt5.ORDER_FILLING_IOC
        else:
            return mt5.ORDER_FILLING_RETURN

    def get_open_position_count(self, symbol):
        """
        Returns the number of open positions for the symbol.
        """
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return 0
        return len(positions)

    def send_order(self, symbol, order_type, lot, sl_points=200, tp_points=400, sl=None, tp=None):
        """
        Calculates and sends an order with protection.
        order_type: mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"{symbol} not found")
            return False

        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"symbol_select({symbol}) failed")
                return False

        point = symbol_info.point
        digits = symbol_info.digits
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Failed to get tick for {symbol}")
            return False

        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # If absolute sl/tp are not provided, calculate based on points
        if sl is None:
            # Ensure SL respects MT5 stops_level (minimum distance from price)
            stops_level = symbol_info.trade_stops_level
            sl_points = max(sl_points, stops_level + 5)
            sl = price - sl_points * point if order_type == mt5.ORDER_TYPE_BUY else price + sl_points * point
            
        if tp is None:
            # Ensure TP respects MT5 stops_level (minimum distance from price)
            stops_level = symbol_info.trade_stops_level
            tp_points = max(tp_points, stops_level + 5)
            tp = price + tp_points * point if order_type == mt5.ORDER_TYPE_BUY else price - tp_points * point

        # Normalize all prices to symbol digits (CRITICAL for 10016 error)
        price = round(price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "magic": 123456,
            "comment": "Institutional Bot Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self.get_filling_mode(symbol),
            "deviation": 20, # 20 points of slippage padding
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            with open("bridge_error.log", "w") as f:
                f.write(f"Retcode: {result.retcode}\n")
                f.write(f"Comment: {result.comment}\n")
            print(f"!!! BRIDGE ERROR: Retcode={result.retcode}, Comment={result.comment} !!!")
            print(f"Order send failed, retcode={result.retcode}")
            return False
        
        print(f"✅ Order successful: {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} {symbol} at {price}")
        return result

    def modify_position_sl(self, ticket, new_sl):
        """
        Modifies the Stop Loss of an existing position.
        """
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
            
        pos = position[0]
        digits = mt5.symbol_info(pos.symbol).digits
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": round(new_sl, digits),
            "tp": pos.tp, # Keep existing TP
            "magic": 123456,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Failed to modify SL for {ticket}: {result.retcode}")
            return False
        print(f"✅ Modified SL for {pos.symbol} to {new_sl}")
        return True

    def close_position(self, ticket):
        """
        Closes a specific position by ticket.
        """
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
            
        pos = position[0]
        symbol = pos.symbol
        lot = pos.volume
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "position": ticket,
            "price": price,
            "magic": 123456,
            "comment": "AI Brain Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self.get_filling_mode(symbol),
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Failed to close position {ticket}: {result.retcode}")
            return False
        return True

    def close_all_positions(self, symbol):
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            for position in positions:
                self.close_position(position.ticket)

    def is_market_open(self, symbol):
        """
        Checks if the market is currently open for a specific symbol.
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False
        
        # 1. Check trade mode (Must be Full or LongOnly/ShortOnly)
        if symbol_info.trade_mode not in [mt5.SYMBOL_TRADE_MODE_FULL, mt5.SYMBOL_TRADE_MODE_LONGONLY, mt5.SYMBOL_TRADE_MODE_SHORTONLY]:
            return False
            
        # 2. Check for fresh activity
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False
            
        # Compare tick time with the symbol's last server time. 
        # If they haven't moved in a while (e.g. 10 mins) during open hours, something is wrong.
        # But specifically for weekends/holidays, the gap will be huge.
        import time
        now = int(time.time())
        
        # If the last tick is from more than 1 hour ago, we treat it as closed 
        # (Crypto trades 24/7, Forex/Gold move constantly when open)
        if (now - tick.time) > 3600: 
            return False
            
        return True

    def disconnect(self):
        mt5.shutdown()
