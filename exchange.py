import heapq
import asyncio
from typing import Any, Dict
from agent_event import EventType, AgentEvent
from order_book import OrderBook
from agents_manager import AgentsManager

class Exchange:
    """Central exchange class managing the market simulation."""
    
    def __init__(self):
        self.priority_queue = []  # Events sorted by timestamp
        self.order_book = OrderBook()
        self.current_time = 0.0
        self.agents_manager = AgentsManager()  # Agent ID -> Agent object
        self.event_handlers = {}  # Event type -> handler function
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.event_handlers[EventType.ORDER_SUBMIT] = self._handle_order_submit
        self.event_handlers[EventType.ORDER_CANCEL] = self._handle_order_cancel
        self.event_handlers[EventType.WAKEUP] = self._handle_wakeup

    
    async def process_events(self, event):
        """Process all events in chronological order."""
        self.current_time = event.timestamp
        
        # Process event with appropriate handler
        handler = self.event_handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            print(f"Unhandled event type: {event.event_type}")
    
    async def _handle_order_submit(self, event: AgentEvent):
        """Handle order submission event."""
        order = event.data
        self.order_book.add_order(order)
        # Try to match orders
        matches = self.order_book.match_orders()
        # Generate match events if needed
        for match in matches:
            match_event = AgentEvent(
                timestamp=self.current_time,
                event_type=EventType.ORDER_MATCH,
                data=match
            )
            self.add_event(match_event)
    
    async def _handle_order_cancel(self, event: AgentEvent):
        """Handle order cancellation event."""
        cancel_data = event.data
        self.order_book.cancel_order(cancel_data['order_id'], cancel_data['side'])
    
    async def _handle_wakeup(self, event: AgentEvent):
        """Handle wakeup event."""
        # Placeholder for wakeup event handling
        pass
    
    async def run(self):
        """Run the exchange by iterating events from agents_manager.run and processing them."""
        # Iterate over events from agents_manager.run
        async for agent_event in self.agents_manager.run():
            # Process all events in chronological order
            await self.process_events(agent_event)