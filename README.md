# Multi-Agent Market Simulator

A high-performance market simulator built with an agent-based architecture that supports millisecond resolution timing and efficient message passing between agents.

## Features

- **Multi-Agent Architecture**: Modular design with different agent types
- **Millisecond Resolution**: Precise timing for high-frequency trading simulations
- **Efficient Event Processing**: Event-driven kernel that avoids polling all agents every millisecond
- **Publish/Subscribe Messaging**: Subscription-based communication system
- **Order Book Management**: Complete limit order book implementation with price-time priority matching
- **Multiple Trading Strategies**: Market maker, momentum, and mean reversion traders
- **Deterministic Execution**: Timestamp-ordered event processing for reproducible simulations

## Architecture Overview

The simulator consists of several key components:

### Kernel
The central component that manages time and schedules events. It uses an event-driven approach to avoid polling all agents every millisecond.

### Message Broker
Implements a publish/subscribe messaging system that routes messages between agents based on topic subscriptions.

### Agents
- **Exchange Agent**: Maintains order books, matches orders, and publishes market data
- **Market Maker Agent**: Provides liquidity by posting bid and ask orders
- **Momentum Trader Agent**: Follows price trends and momentum signals
- **Mean Reversion Trader Agent**: Trades against extreme price movements

### Order Book
Efficient limit order book implementation with price-time priority matching algorithm.


## Usage

Run the simulation with:

```bash
python examples/main.py
```

This will run a sample simulation with AAPL symbol and multiple trading agents for 10 seconds.

To run the order book depth example:

```bash
python examples/order_book_depth_example.py
```

This will run a simulation demonstrating order book depth checking functionality.

## Code Structure

### Core Components
- `core/agent.py`: Base agent classes and communication interfaces
- `core/kernel.py`: Event scheduler and simulation coordinator
- `core/message.py`: Publish/subscribe messaging system
- `core/exchange.py`: Exchange agent with order matching

### Order Book
- `orderbook/order_book.py`: Limit order book implementation
- `orderbook/order_book_utils.py`: Utility functions for order book operations

### Agents
- `agents/trading_agents.py`: Various trading strategy implementations

### Examples
- `examples/main.py`: Sample simulation setup and execution
- `examples/order_book_depth_example.py`: Example demonstrating order book depth checking

### Utilities
- `utils/logger.py`: Logging utilities

### Tests
- `tests/test_liquidity_provider.py`: Unit tests for liquidity provider agent
- `tests/test_order_book.py`: Unit tests for order book functionality

## Performance Optimizations

- **Event-Driven Processing**: Agents only wake up when they have work to do
- **Subscription-Based Messaging**: Agents only receive messages they're interested in
- **Efficient Data Structures**: Uses sorted containers for order book operations
- **Batch Message Processing**: Groups messages by recipient for efficient delivery
- **Sparse Time Representation**: Only processes timestamps with scheduled events

## Customization

To create your own trading agents:

1. Extend the `ActiveAgent` or `PassiveAgent` base class from `core.agent`
2. Implement the `receive_message` method to process market data
3. Implement the `wakeup` method for scheduled actions
4. Use `send_message` to submit orders or other messages
5. Use `subscribe` to receive relevant market data

Example:
```python
from core.agent import ActiveAgent
from core.message import Message

class MyCustomAgent(ActiveAgent):
    def __init__(self, agent_id: str, symbol: str):
        super().__init__(agent_id)
        self.symbol = symbol
    
    def receive_message(self, message: Message):
        # Process incoming messages
        pass
    
    def wakeup(self, current_time: int):
        super().wakeup(current_time)
        # Perform scheduled actions
        pass
```

## License

MIT License