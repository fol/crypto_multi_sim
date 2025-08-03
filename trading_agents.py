from typing import Dict, List, Tuple
from agent import ActiveAgent
from message import Message
from logger import setup_logger
import random


class MarketMakerAgent(ActiveAgent):
    """Market maker agent that provides liquidity by posting bids and asks"""
    
    def __init__(self, agent_id: str, symbol: str, fair_value: float, spread: float = 0.02):
        super().__init__(agent_id)
        self.symbol = symbol
        self.fair_value = fair_value
        self.spread = spread
        self.inventory = 0
        self.max_inventory = 100
        self.order_size = 10
        self.active_orders = {}  # order_id -> side
        self.logger = setup_logger(f"MarketMakerAgent.{agent_id}")
    
    def initialize(self):
        """Initialize subscriptions and first orders"""
        # Subscribe to relevant market data
        self.subscribe(f"{self.symbol}.ORDERBOOK")
        self.subscribe(f"{self.symbol}.PRICE")
        self.subscribe(f"{self.symbol}.TRADE")
        
        # Schedule first wakeup to place orders
        self.schedule_wakeup(1000)  # Place first orders after 1 second
    
    def receive_message(self, message: Message):
        """Process incoming market data"""
        if message.topic == f"{self.symbol}.PRICE":
            self._update_fair_value(message.payload)
        elif message.topic == f"{self.symbol}.TRADE":
            self._process_trade(message.payload)
        elif message.topic == f"{self.symbol}.ORDERBOOK":
            self._update_quotes(message.payload)
    
    def _update_fair_value(self, price_data: dict):
        """Update fair value based on market prices"""
        best_bid = price_data.get("best_bid", 0)
        best_ask = price_data.get("best_ask", 0)
        
        if best_bid > 0 and best_ask < float('inf'):
            self.fair_value = (best_bid + best_ask) / 2
    
    def _process_trade(self, trade_data: dict):
        """Process trade executions"""
        # Update inventory based on our trades
        pass  # Implementation would track our order executions
    
    def _update_quotes(self, orderbook_data: dict):
        """Update quotes based on order book"""
        # Adjust quotes based on order book depth
        pass  # Implementation would adjust based on competition
    
    def wakeup(self, current_time: int):
        """Place or adjust quotes"""
        super().wakeup(current_time)
        self.logger.info(f"MarketMakerAgent {self.agent_id} waking up at {current_time}ms")
        
        # Cancel existing orders
        self._cancel_existing_orders()
        
        # Place new orders if within inventory limits
        if abs(self.inventory) < self.max_inventory:
            self._place_quotes()
        
        # Schedule next wakeup
        self.schedule_wakeup(current_time + 500)  # Adjust quotes every 500ms
    
    def _cancel_existing_orders(self):
        """Cancel all existing orders"""
        for order_id in list(self.active_orders.keys()):
            cancel_message = {
                "order_id": order_id,
                "symbol": self.symbol
            }
            self.send_message(f"{self.symbol}.CANCEL", cancel_message)
            del self.active_orders[order_id]
    
    def _place_quotes(self):
        """Place new bid and ask orders"""
        bid_price = round(self.fair_value * (1 - self.spread/2), 2)
        ask_price = round(self.fair_value * (1 + self.spread/2), 2)
        
        self.logger.info(f"Placing quotes: BID {bid_price} ASK {ask_price}")
        
        # Place bid
        bid_id = f"{self.agent_id}_BID_{int(round(bid_price * 100))}"
        bid_order = {
            "order_id": bid_id,
            "symbol": self.symbol,
            "side": "BUY",
            "price": bid_price,
            "quantity": self.order_size
        }
        self.send_message(f"{self.symbol}.ORDER", bid_order)
        self.active_orders[bid_id] = "BUY"
        
        # Place ask
        ask_id = f"{self.agent_id}_ASK_{int(round(ask_price * 100))}"
        ask_order = {
            "order_id": ask_id,
            "symbol": self.symbol,
            "side": "SELL",
            "price": ask_price,
            "quantity": self.order_size
        }
        self.send_message(f"{self.symbol}.ORDER", ask_order)
        self.active_orders[ask_id] = "SELL"


class MomentumTraderAgent(ActiveAgent):
    """Momentum trader that follows price trends"""
    
    def __init__(self, agent_id: str, symbol: str):
        super().__init__(agent_id)
        self.symbol = symbol
        self.price_history = []
        self.max_history = 10
        self.position = 0
        self.max_position = 100
        self.logger = setup_logger(f"MomentumTraderAgent.{agent_id}")
    
    def initialize(self):
        """Initialize subscriptions"""
        self.subscribe(f"{self.symbol}.PRICE")
        self.subscribe(f"{self.symbol}.TRADE")
    
    def receive_message(self, message: Message):
        """Process incoming market data"""
        if message.topic == f"{self.symbol}.PRICE":
            self._process_price_update(message.payload, message.timestamp)
        elif message.topic == f"{self.symbol}.TRADE":
            self._process_trade(message.payload)
    
    def _process_price_update(self, price_data: dict, timestamp: int):
        """Process price updates and check for momentum signals"""
        best_bid = price_data.get("best_bid", 0)
        best_ask = price_data.get("best_ask", 0)
        
        if best_bid > 0 and best_ask < float('inf'):
            mid_price = (best_bid + best_ask) / 2
            self.price_history.append((timestamp, mid_price))
            
            # Keep only recent history
            if len(self.price_history) > self.max_history:
                self.price_history.pop(0)
            
            # Check for momentum signal
            if len(self.price_history) >= 5:
                self._check_momentum_signal()
    
    def _check_momentum_signal(self):
        """Check for momentum trading signals"""
        if len(self.price_history) < 5:
            return
        
        # Simple momentum: check if price is trending up or down
        recent_prices = [price for _, price in self.price_history[-5:]]
        price_change = recent_prices[-1] - recent_prices[0]
        
        # Buy if strong upward momentum
        if price_change > 0.05 and self.position < self.max_position:
            self._place_order("BUY")
        # Sell if strong downward momentum
        elif price_change < -0.05 and self.position > -self.max_position:
            self._place_order("SELL")
    
    def _place_order(self, side: str):
        """Place a market order"""
        if len(self.price_history) == 0:
            return
        
        current_price = self.price_history[-1][1]
        order_size = 10
        
        order = {
            "order_id": f"{self.agent_id}_{side}_{int(round(current_price * 100))}",
            "symbol": self.symbol,
            "side": side,
            "price": current_price * (0.995 if side == "BUY" else 1.005),  # Limit order near market
            "quantity": order_size
        }
        self.send_message(f"{self.symbol}.ORDER", order)
    
    def _process_trade(self, trade_data: dict):
        """Process trade executions to update position"""
        pass  # Implementation would track position changes


class MeanReversionTraderAgent(ActiveAgent):
    """Mean reversion trader that trades against extreme price movements"""
    
    def __init__(self, agent_id: str, symbol: str):
        super().__init__(agent_id)
        self.symbol = symbol
        self.price_history = []
        self.max_history = 20
        self.position = 0
        self.max_position = 100
        self.fair_value = 100.0  # Initial fair value
        self.logger = setup_logger(f"MeanReversionTraderAgent.{agent_id}")
    
    def initialize(self):
        """Initialize subscriptions"""
        self.subscribe(f"{self.symbol}.PRICE")
        self.subscribe(f"{self.symbol}.STATS")
    
    def receive_message(self, message: Message):
        """Process incoming market data"""
        if message.topic == f"{self.symbol}.PRICE":
            self._process_price_update(message.payload, message.timestamp)
        elif message.topic == f"{self.symbol}.STATS":
            self._update_fair_value(message.payload)
    
    def _process_price_update(self, price_data: dict, timestamp: int):
        """Process price updates and check for mean reversion signals"""
        best_bid = price_data.get("best_bid", 0)
        best_ask = price_data.get("best_ask", 0)
        
        if best_bid > 0 and best_ask < float('inf'):
            mid_price = (best_bid + best_ask) / 2
            self.price_history.append((timestamp, mid_price))
            
            # Keep only recent history
            if len(self.price_history) > self.max_history:
                self.price_history.pop(0)
            
            # Check for mean reversion signal
            self._check_mean_reversion_signal(mid_price)
    
    def _update_fair_value(self, stats_data: dict):
        """Update fair value based on market statistics"""
        vwap = stats_data.get("vwap", self.fair_value)
        if vwap > 0:
            self.fair_value = vwap
    
    def _check_mean_reversion_signal(self, current_price: float):
        """Check for mean reversion trading signals"""
        if len(self.price_history) < 10:
            return
        
        # Calculate price deviation from fair value
        deviation = current_price - self.fair_value
        
        # Buy if price is significantly below fair value
        if deviation < -1.0 and self.position < self.max_position:
            self._place_order("BUY")
        # Sell if price is significantly above fair value
        elif deviation > 1.0 and self.position > -self.max_position:
            self._place_order("SELL")
    
    def _place_order(self, side: str):
        """Place a limit order"""
        if len(self.price_history) == 0:
            return
        
        current_price = self.price_history[-1][1]
        order_size = 15
        
        # Place limit order closer to fair value
        limit_price = (current_price + self.fair_value) / 2
        if side == "SELL":
            limit_price = (current_price + self.fair_value) / 2
            
        order = {
            "order_id": f"{self.agent_id}_{side}_{int(round(limit_price * 100))}",
            "symbol": self.symbol,
            "side": side,
            "price": round(limit_price, 2),
            "quantity": order_size
        }
        self.send_message(f"{self.symbol}.ORDER", order)