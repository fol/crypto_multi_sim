from abc import ABC, abstractmethod
from typing import AsyncGenerator
import asyncio
from agent_event import AgentEvent, EventType
from exchange import Exchange


class Agent(ABC):
    """Base agent class for market participants."""
    
    def __init__(self, agent_id: str, exchange: Exchange):
        self.id = agent_id
        self.exchange = exchange
        self.event_generator = self.generate_events()
        exchange.add_agent(self)
    
    @abstractmethod
    async def generate_events(self) -> AsyncGenerator[AgentEvent, None]:
        """Generate events for this agent. Should be implemented by subclasses."""
        pass
    


# Example implementation of a simple trader agent
class SimpleTraderAgent(Agent):
    """Simple trader agent that submits random orders."""
    
    def __init__(self, agent_id: str, exchange: Exchange, initial_price: float):
        self.initial_price = initial_price
        self.order_count = 0
        super().__init__(agent_id, exchange)
    
    async def generate_events(self) -> AsyncGenerator[AgentEvent, None]:
        """Generate trading events."""
        # Submit first order immediately
        yield self._create_order_event(self.exchange.current_time)
        
        # Schedule next wakeup
        next_time = self.exchange.current_time + 1000  # 1 second later
        yield self.schedule_wakeup(next_time)
    
    def _create_order_event(self, timestamp: float) -> AgentEvent:
        """Create an order event."""
        self.order_count += 1
        order = {
            'id': f"{self.id}_order_{self.order_count}",
            'side': 'buy' if self.order_count % 2 == 1 else 'sell',
            'price': self.initial_price + (1 if self.order_count % 2 == 1 else -1) * (self.order_count % 10),
            'quantity': 1 + (self.order_count % 5),
            'timestamp': timestamp
        }
        
        return AgentEvent(
            timestamp=timestamp,
            event_type=EventType.ORDER_SUBMIT,
            data=order
        )