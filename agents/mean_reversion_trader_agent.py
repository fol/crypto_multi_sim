from typing import Dict, List, Tuple
from core.agent import ActiveAgent
from core.message import Message
from utils.logger import setup_logger
import random


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