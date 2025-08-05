from typing import Dict, List, Tuple
from core.agent import ActiveAgent
from core.message import Message
from utils.logger import setup_logger
import random


class LiquidityProviderAgent(ActiveAgent):
    """Liquidity provider agent that places limit orders to create liquidity and makes random market trades"""
    
    def __init__(self, agent_id: str, symbol: str):
        super().__init__(agent_id)
        self.symbol = symbol
        self.logger = setup_logger(f"LiquidityProviderAgent.{agent_id}")
        
        # Liquidity provision parameters
        self.initial_fair_value = 100.0
        self.spread = 0.02  # 2% spread
        self.limit_order_size = 20
        self.market_order_size = 10
        self.max_orders_per_side = 5
        
        # State tracking
        self.active_limit_orders = {}  # order_id -> side
        self.last_order_book_state = None
        self.liquidity_provision_interval = 1000  # Place liquidity every 1000ms
        self.market_trade_interval = 2000  # Make market trades every 2000ms
        self.last_liquidity_provision = 0
        self.last_market_trade = 0
    
    def initialize(self):
        """Initialize subscriptions and schedule first actions"""
        # Subscribe to relevant market data
        self.subscribe(f"{self.symbol}.ORDERBOOK")
        self.subscribe(f"{self.symbol}.PRICE")
        
        # Schedule first actions
        self.schedule_wakeup(500)  # First wakeup after 500ms
    
    def receive_message(self, message: Message):
        """Process incoming market data"""
        if message.topic == f"{self.symbol}.ORDERBOOK":
            self.last_order_book_state = message.payload
        elif message.topic == f"{self.symbol}.PRICE":
            # Update fair value based on market prices if needed
            pass
    
    def wakeup(self, current_time: int):
        """Called periodically to place limit orders and market trades"""
        super().wakeup(current_time)
        self.logger.debug(f"LiquidityProviderAgent {self.agent_id} waking up at {current_time}ms")
        
        # Place limit orders to create liquidity if order book is empty or enough time has passed
        if (current_time - self.last_liquidity_provision >= self.liquidity_provision_interval or 
            self._is_order_book_empty()):
            self._place_limit_orders(current_time)
            self.last_liquidity_provision = current_time
        
        # Make random market trades
        if current_time - self.last_market_trade >= self.market_trade_interval:
            self._make_random_market_trade(current_time)
            self.last_market_trade = current_time
        
        # Schedule next wakeup
        next_wakeup = min(
            self.last_liquidity_provision + self.liquidity_provision_interval,
            self.last_market_trade + self.market_trade_interval
        )
        # Ensure we wake up at least once per second
        next_wakeup = min(next_wakeup, current_time + 1000)
        self.schedule_wakeup(next_wakeup)
    
    def _is_order_book_empty(self) -> bool:
        """Check if the order book is empty or nearly empty"""
        if self.last_order_book_state is None:
            return True
            
        bids = self.last_order_book_state.get("bids", [])
        asks = self.last_order_book_state.get("asks", [])
        
        # Consider order book empty if less than 2 levels on each side
        return len(bids) < 2 and len(asks) < 2
    
    def _place_limit_orders(self, current_time: int):
        """Place limit orders to create liquidity"""
        self.logger.info(f"Placing limit orders to create liquidity at time {current_time}ms")
        
        # Cancel existing limit orders first
        self._cancel_existing_limit_orders()
        
        # Determine fair value for pricing
        fair_value = self.initial_fair_value
        if self.last_order_book_state:
            best_bid = self.last_order_book_state.get("best_bid", 0)
            best_ask = self.last_order_book_state.get("best_ask", float('inf'))
            if best_bid > 0 and best_ask < float('inf'):
                fair_value = (best_bid + best_ask) / 2
            elif best_bid > 0:
                fair_value = best_bid
            elif best_ask < float('inf'):
                fair_value = best_ask
        
        # Place multiple levels of limit orders on both sides
        for i in range(self.max_orders_per_side):
            # Place bid orders (BUY)
            bid_price = round(fair_value * (1 - self.spread/2 - i * 0.005), 2)
            bid_id = f"{self.agent_id}_BID_{i}_{current_time}"
            bid_order = {
                "order_id": bid_id,
                "symbol": self.symbol,
                "side": "BUY",
                "price": bid_price,
                "quantity": self.limit_order_size
            }
            self.send_message(f"{self.symbol}.ORDER", bid_order)
            self.active_limit_orders[bid_id] = "BUY"
            
            # Place ask orders (SELL)
            ask_price = round(fair_value * (1 + self.spread/2 + i * 0.005), 2)
            ask_id = f"{self.agent_id}_ASK_{i}_{current_time}"
            ask_order = {
                "order_id": ask_id,
                "symbol": self.symbol,
                "side": "SELL",
                "price": ask_price,
                "quantity": self.limit_order_size
            }
            self.send_message(f"{self.symbol}.ORDER", ask_order)
            self.active_limit_orders[ask_id] = "SELL"
    
    def _cancel_existing_limit_orders(self):
        """Cancel all existing limit orders"""
        for order_id in list(self.active_limit_orders.keys()):
            cancel_message = {
                "order_id": order_id,
                "symbol": self.symbol
            }
            self.send_message(f"{self.symbol}.CANCEL", cancel_message)
        self.active_limit_orders.clear()
    
    def _make_random_market_trade(self, current_time: int):
        """Make a random market trade"""
        self.logger.info(f"Making random market trade at time {current_time}ms")
        
        # Randomly decide to buy or sell
        side = random.choice(["BUY", "SELL"])
        
        # Determine price reference for market order
        price_reference = self.initial_fair_value
        if self.last_order_book_state:
            best_bid = self.last_order_book_state.get("best_bid", 0)
            best_ask = self.last_order_book_state.get("best_ask", float('inf'))
            if side == "BUY" and best_ask < float('inf'):
                price_reference = best_ask
            elif side == "SELL" and best_bid > 0:
                price_reference = best_bid
        
        # For market orders, we use special price values:
        # - BUY market orders: price = float('inf')
        # - SELL market orders: price = 0.0
        market_price = float('inf') if side == "BUY" else 0.0
        
        order_id = f"{self.agent_id}_MARKET_{side}_{current_time}"
        market_order = {
            "order_id": order_id,
            "symbol": self.symbol,
            "side": side,
            "price": market_price,
            "quantity": self.market_order_size
        }
        self.send_message(f"{self.symbol}.ORDER", market_order)