from kernel import Kernel
from exchange import ExchangeAgent
from trading_agents import MarketMakerAgent, MomentumTraderAgent, MeanReversionTraderAgent
import random


def main():
    """Main function to run the market simulation"""
    # Create kernel
    kernel = Kernel()
    
    # Create exchange agent
    exchange = ExchangeAgent("EXCHANGE")
    kernel.register_agent(exchange)
    
    # Initialize a symbol
    exchange.initialize_symbol("AAPL")
    
    # Create trading agents
    market_maker = MarketMakerAgent("MM_1", "AAPL", 100.0, 0.02)
    momentum_trader = MomentumTraderAgent("MOM_1", "AAPL")
    mean_reversion_trader = MeanReversionTraderAgent("MR_1", "AAPL")
    
    # Register agents
    kernel.register_agent(market_maker)
    kernel.register_agent(momentum_trader)
    kernel.register_agent(mean_reversion_trader)
    
    # Initialize agents
    market_maker.initialize()
    momentum_trader.initialize()
    mean_reversion_trader.initialize()
    
    # Schedule some initial events
    kernel.schedule_agent_wakeup("EXCHANGE", 100)
    kernel.schedule_agent_wakeup("MM_1", 1000)
    kernel.schedule_agent_wakeup("MOM_1", 2000)
    kernel.schedule_agent_wakeup("MR_1", 3000)
    
    # Run simulation for 10 seconds (10000 milliseconds)
    print("Starting market simulation...")
    kernel.run(10000)
    print("Simulation completed.")
    
    # Print some statistics
    print(f"Final time: {kernel.get_current_time()} ms")
    print(f"Total trades: {len(exchange.trade_history)}")
    print(f"Order book size: {len(exchange.order_books['AAPL'].bids) + len(exchange.order_books['AAPL'].asks)} levels")
    
    if exchange.trade_history:
        last_trades = exchange.trade_history[-5:]  # Last 5 trades
        print("Last 5 trades:")
        for trade in last_trades:
            print(f"  {trade.trade_id}: {trade.quantity} @ ${trade.price}")


if __name__ == "__main__":
    main()