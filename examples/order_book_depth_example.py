#!/usr/bin/env python3
"""
Example demonstrating how to use the order book depth checking functionality
in any trading agent.
"""

from ..agents.trading_agents import MarketMakerAgent, MomentumTraderAgent
from ..core.exchange import ExchangeAgent
from ..core.kernel import Kernel
from ..core.message import Message, MessageBroker
from ..orderbook.order_book_utils import OrderBookDepthChecker
import time


class SmartTraderAgent(MomentumTraderAgent):
    """Example trader that uses order book depth checking before placing orders"""
    
    def __init__(self, agent_id: str, symbol: str):
        super().__init__(agent_id, symbol)
        self.depth_checker = None
        self.safe_order_placer = None
    
    def initialize(self):
        """Initialize the agent and order book utilities"""
        super().initialize()
        
        # Initialize order book depth checking utilities
        self.depth_checker = OrderBookDepthChecker(self, self.symbol)
        
        # Subscribe to market depth responses
        self.subscribe(f"{self.symbol}.MARKET_DEPTH_RESPONSE")
    
    def receive_message(self, message: Message):
        """Process incoming messages"""
        super().receive_message(message)
        
        # Handle market depth responses
        if message.topic == f"{self.symbol}.MARKET_DEPTH_RESPONSE":
            self.depth_checker.handle_market_depth_response(message)
    
    def check_liquidity_before_trading(self):
        """Example of checking liquidity before placing an order"""
        def handle_liquidity_score(response):
            score = response.get("liquidity_score", 0.0)
            self.logger.info(f"Current liquidity score: {score:.2f}")
            
            if score > 0.5:
                self.logger.info("High liquidity detected, safe to place larger orders")
            elif score > 0.2:
                self.logger.info("Moderate liquidity, place medium orders with caution")
            else:
                self.logger.info("Low liquidity, be careful with order sizes")
        
        self.depth_checker.get_liquidity_score(reference_quantity=50, callback=handle_liquidity_score)
    
    def check_order_impact(self, side: str, quantity: int):
        """Example of checking the impact of an order before placing it"""
        def handle_impact(average_price, slippage_bps, fill_percent):
            self.logger.info(f"Order impact for {side} {quantity}:")
            self.logger.info(f"  Average price: {average_price:.2f}")
            self.logger.info(f"  Slippage: {slippage_bps:.1f} bps")
            self.logger.info(f"  Fill percentage: {fill_percent:.2%}")
            
            if slippage_bps > 10:  # More than 10 bps slippage
                self.logger.warning("High slippage expected, consider reducing order size")
        
        self.depth_checker.get_average_price_for_quantity(side, quantity, callback=handle_impact)
    
    def place_safe_order(self, side: str, quantity: int):
        """Example of placing a market order (liquidity checking now happens in OrderBook)"""
        order = {
            "order_id": f"{self.agent_id}_{side}_MARKET_{int(time.time() * 1000)}",
            "symbol": self.symbol,
            "side": side,
            "price": float('inf') if side == 'BUY' else 0.0,  # Market order
            "quantity": quantity
        }
        self.send_message(f"{self.symbol}.ORDER", order)
        self.logger.info(f"Placed market {side} order for {quantity} shares (liquidity check in OrderBook)")
    
    def get_market_spread(self):
        """Example of getting the current bid-ask spread"""
        def handle_spread(spread):
            self.logger.info(f"Current spread: {spread:.2f}")
        
        self.depth_checker.get_spread(callback=handle_spread)
    
    def get_market_imbalance(self):
        """Example of getting order book imbalance"""
        def handle_imbalance(imbalance):
            if imbalance > 0.1:
                self.logger.info("Market shows buying pressure (bullish)")
            elif imbalance < -0.1:
                self.logger.info("Market shows selling pressure (bearish)")
            else:
                self.logger.info("Market is balanced")
        
        self.depth_checker.get_imbalance(callback=handle_imbalance)


def main():
    """Run the example simulation"""
    # Initialize the simulation components
    kernel = Kernel()
    message_broker = MessageBroker()
    
    # Create and configure agents
    exchange = ExchangeAgent("EXCHANGE")
    market_maker = MarketMakerAgent("MARKET_MAKER", "BTCUSD", fair_value=50000.0, spread=0.01)
    smart_trader = SmartTraderAgent("SMART_TRADER", "BTCUSD")
    
    # Set up message broker connections
    for agent in [exchange, market_maker, smart_trader]:
        agent.set_message_broker(message_broker)
        agent.set_kernel(kernel)
    
    # Register agents with kernel
    for agent in [exchange, market_maker, smart_trader]:
        kernel.register_agent(agent)
    
    # Initialize the exchange with the trading symbol
    exchange.initialize_symbol("BTCUSD")
    
    # Initialize the agents
    market_maker.initialize()
    smart_trader.initialize()
    
    # Schedule market maker to run for a period of time
    print("=== Starting simulation ===")
    # Run the simulation for 5 seconds to let the market maker place orders
    kernel.run(5000)  # Run for 5000ms (5 seconds)
    
    # Now demonstrate the order book depth checking functionality
    # These functions send messages which will be processed in subsequent kernel runs
    
    print("\n=== Example 1: Checking liquidity score ===")
    smart_trader.check_liquidity_before_trading()
    kernel.run(1000)  # Run for 1 more second to process messages
    
    print("\n=== Example 2: Checking order impact ===")
    smart_trader.check_order_impact("BUY", 20)
    kernel.run(1000)  # Run for 1 more second to process messages
    
    print("\n=== Example 3: Getting market spread ===")
    smart_trader.get_market_spread()
    kernel.run(1000)  # Run for 1 more second to process messages
    
    print("\n=== Example 4: Getting market imbalance ===")
    smart_trader.get_market_imbalance()
    kernel.run(1000)  # Run for 1 more second to process messages
    
    print("\n=== Example 5: Placing a safe market order ===")
    smart_trader.place_safe_order("BUY", 15)
    kernel.run(2000)  # Run for 2 more seconds to process messages and orders
    
    print("\n=== Example 6: Attempting to place a large order (may fail) ===")
    smart_trader.place_safe_order("BUY", 200)
    kernel.run(2000)  # Run for 2 more seconds to process messages and orders
    
    print("\n=== Simulation Complete ===")


if __name__ == "__main__":
    main()