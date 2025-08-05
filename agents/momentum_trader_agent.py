from typing import Dict, List, Tuple
from core.agent import ActiveAgent
from core.message import Message
from utils.logger import setup_logger
import random


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