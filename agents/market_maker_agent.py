from typing import Dict, List, Tuple
from core.agent import ActiveAgent
from core.message import Message
from utils.logger import setup_logger
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