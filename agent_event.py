import heapq
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class EventType(Enum):
    """Enumeration of event types in the market simulator."""
    ORDER_SUBMIT = "order_submit"
    ORDER_CANCEL = "order_cancel"
    ORDER_MATCH = "order_match"
    MARKET_DATA = "market_data"
    WAKEUP = "wakeup"


@dataclass
class AgentEvent:
    """Base event class with timestamp for priority queue sorting."""
    timestamp: float  # Millisecond timestamp
    event_type: EventType
    data: Any = None
    priority: int = 0  # Lower numbers = higher priority

    def __lt__(self, other):
        """For priority queue ordering: primary by timestamp, secondary by priority."""
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.priority < other.priority