import asyncio
from exchange import Exchange
from agents import SimpleTraderAgent


# Example usage
async def main():
    # Create exchange
    exchange = Exchange()
    
    # Create agents
    trader1 = SimpleTraderAgent("trader1", exchange, 50000.0)  # BTC price
    trader2 = SimpleTraderAgent("trader2", exchange, 50000.0)
    
    # Schedule initial wakeup events for agents
    exchange.add_event(trader1.schedule_wakeup(0))
    exchange.add_event(trader2.schedule_wakeup(500))  # 0.5 seconds later
    
    # Process events
    await exchange.process_events()
    
    print("Simulation completed")
    print(f"Final time: {exchange.current_time} ms")
    print(f"Best bid: {exchange.order_book.get_best_bid()}")
    print(f"Best ask: {exchange.order_book.get_best_ask()}")
    print(f"Trades executed: {len(exchange.order_book.trades)}")

if __name__ == "__main__":
    asyncio.run(main())