import MetaTrader5 as mt5
import pandas as pd
import time
from config.security_vault import SecurityVault


class MT5Bridge:
    def __init__(self, config):
        self.config = config
        self.vault = SecurityVault()
        # Cache master credentials
        self.master_credentials = self.vault.get_credentials()
        self.current_login = None
        
    def connect(self, credentials=None, retries=3):
        """
        Connects to an MT5 account. If no credentials provided, uses Master.
        """
        target = credentials if credentials else self.master_credentials
        
        if not target or target.get('login') is None or str(target.get('login')) == '0':
            return False
            
        for attempt in range(retries):
            # 1. Initialize (Don't shutdown if already working)
            if not mt5.initialize():
                print(f"MT5 terminal initialization failed. Attempt {attempt+1}. Error: {mt5.last_error()}")
                # ONLY shutdown if initialization failed and we have retries left
                mt5.shutdown()
                time.sleep(2.0)
                if not mt5.initialize():
                    print(f"Hard retry failed. Error: {mt5.last_error()}")
                    continue

            # 2. Perform Login
            login_id = int(target.get('login'))
            password = target.get('password')
            server = target.get('server')
            
            print(f"Attempting login to {server} (Account: {login_id})...")
            success = mt5.login(login=login_id, password=password, server=server)
            
            if success:
                self.current_login = target.get('login')
                print(f"Connected to {server} - Account: {self.current_login}")
                
                # Ensure all configured symbols are visible
                if 'symbols' in self.config:
                    for symbol in self.config['symbols'].keys():
                        mt5.symbol_select(symbol, True)
                return True
            else:
                err_code, err_msg = mt5.last_error()
                print(f"❌ Login failed. Account: {login_id}, Server: {server}. Error [{err_code}]: {err_msg}")
                # Common errors: 10015 (Invalid account), 10018 (Market closed), -5 (Invalid params)
                time.sleep(1)
        
        return False

    def switch_account(self, credentials):
        """
        Fast switch between accounts without full shutdown if possible.
        """
        if str(self.current_login) == str(credentials.get('login')):
            return True
            
        return self.connect(credentials, retries=2)

    def get_data(self, symbol, timeframe, n=100):
        """
        Fetches 'n' bars of historical data. If 'n' is beyond broker limits, 
        it intelligently scales down to the maximum available.
        """
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
        
        # If None, try to get as much as possible by checking available bars
        if rates is None or len(rates) == 0:
            terminal_info = mt5.terminal_info()
            # Try to get at least 10,000 or the max allowed by the terminal
            max_bars = getattr(terminal_info, 'maxbars', 100000)
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, min(n, max_bars))
            
            # If still None, the symbol might just not be synced
            if rates is None or len(rates) == 0:
                cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
                return pd.DataFrame(columns=cols)

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_mtf_data(self, symbol):
        """
        Returns a dictionary of dataframes for different timeframes.
        """
        return {
            "M1": self.get_data(symbol, mt5.TIMEFRAME_M1, 250),
            "M5": self.get_data(symbol, mt5.TIMEFRAME_M5, 200),
            "M15": self.get_data(symbol, mt5.TIMEFRAME_M15, 200),
            "H1": self.get_data(symbol, mt5.TIMEFRAME_H1, 100),
            "H4": self.get_data(symbol, mt5.TIMEFRAME_H4, 100)
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
        symbol_info = mt5.symbol_info(pos.symbol)
        digits = symbol_info.digits
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
        
        tick = mt5.symbol_info_tick(symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
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
        now = int(time.time())
        
        # If the last tick is from more than 1 hour ago, we treat it as closed 
        # (Crypto trades 24/7, Forex/Gold move constantly when open)
        if (now - tick.time) > 3600: 
            return False
            
        return True

    def disconnect(self):
        mt5.shutdown()
