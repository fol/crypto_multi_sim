import heapq
from typing import Dict, List, Set, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from logger import setup_logger


@dataclass
class Message:
    """Base message class for inter-agent communication"""
    timestamp: int  # milliseconds since simulation start
    topic: str      # topic identifier
    payload: dict   # message content
    source_id: str  # sending agent ID
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __lt__(self, other):
        """Enable comparison for heap operations"""
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        return self.message_id < other.message_id
    
    def __le__(self, other):
        """Enable comparison for heap operations"""
        if self.timestamp != other.timestamp:
            return self.timestamp <= other.timestamp
        return self.message_id <= other.message_id
    
    def __gt__(self, other):
        """Enable comparison for heap operations"""
        if self.timestamp != other.timestamp:
            return self.timestamp > other.timestamp
        return self.message_id > other.message_id
    
    def __ge__(self, other):
        """Enable comparison for heap operations"""
        if self.timestamp != other.timestamp:
            return self.timestamp >= other.timestamp
        return self.message_id >= other.message_id


class MessageBroker:
    """Publish/Subscribe messaging system for agent communication"""
    
    def __init__(self):
        # Subscription registry: topic -> set of agent IDs
        self.subscriptions: Dict[str, Set[str]] = {}
        # Wildcard subscriptions: pattern -> set of agent IDs
        self.wildcard_subscriptions: Dict[str, Set[str]] = {}
        # Message queue ordered by timestamp
        self.message_queue: List[tuple] = []  # (timestamp, message)
        # Agent message handlers
        self.agent_handlers: Dict[str, Callable] = {}
        self.logger = setup_logger("MessageBroker")
    
    def subscribe(self, agent_id: str, topic_pattern: str):
        """Subscribe an agent to a topic or pattern"""
        if "*" in topic_pattern:
            # Handle wildcard patterns
            if topic_pattern not in self.wildcard_subscriptions:
                self.wildcard_subscriptions[topic_pattern] = set()
            self.wildcard_subscriptions[topic_pattern].add(agent_id)
        else:
            # Handle exact topics
            if topic_pattern not in self.subscriptions:
                self.subscriptions[topic_pattern] = set()
            self.subscriptions[topic_pattern].add(agent_id)
    
    def unsubscribe(self, agent_id: str, topic_pattern: str):
        """Unsubscribe an agent from a topic or pattern"""
        if "*" in topic_pattern:
            if topic_pattern in self.wildcard_subscriptions:
                self.wildcard_subscriptions[topic_pattern].discard(agent_id)
        else:
            if topic_pattern in self.subscriptions:
                self.subscriptions[topic_pattern].discard(agent_id)
    
    def publish(self, message: Message):
        """Publish a message to all subscribed agents"""
        self.logger.debug(f"Publishing message to topic {message.topic}")
        heapq.heappush(self.message_queue, (message.timestamp, message))
    
    def register_agent_handler(self, agent_id: str, handler: Callable):
        """Register an agent's message handling function"""
        self.agent_handlers[agent_id] = handler
    
    def get_messages_for_timestamp(self, timestamp: int) -> List[Message]:
        """Get all messages scheduled for a specific timestamp"""
        messages = []
        while self.message_queue and self.message_queue[0][0] <= timestamp:
            _, message = heapq.heappop(self.message_queue)
            messages.append(message)
        return messages
    
    def deliver_messages(self, timestamp: int):
        """Deliver all messages scheduled for the current timestamp"""
        messages = self.get_messages_for_timestamp(timestamp)
        self.logger.debug(f"Delivering {len(messages)} messages at timestamp {timestamp}")
        
        # Group messages by recipient for batch delivery
        recipient_messages: Dict[str, List[Message]] = {}
        
        for message in messages:
            # Find all agents subscribed to this message's topic
            recipients = self._find_recipients(message.topic)
            
            for recipient_id in recipients:
                if recipient_id not in recipient_messages:
                    recipient_messages[recipient_id] = []
                recipient_messages[recipient_id].append(message)
        
        # Deliver messages to each recipient
        for recipient_id, msgs in recipient_messages.items():
            if recipient_id in self.agent_handlers:
                self.logger.debug(f"Delivering {len(msgs)} messages to agent {recipient_id}")
                for message in msgs:
                    self.agent_handlers[recipient_id](message)
    
    def _find_recipients(self, topic: str) -> Set[str]:
        """Find all agents subscribed to a topic (including wildcards)"""
        recipients = set()
        
        # Exact matches
        if topic in self.subscriptions:
            recipients.update(self.subscriptions[topic])
        
        # Wildcard matches
        for pattern, agents in self.wildcard_subscriptions.items():
            if self._matches_pattern(topic, pattern):
                recipients.update(agents)
        
        return recipients
    
    def _matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a wildcard pattern"""
        if pattern == "*":
            return True
        
        if "*" not in pattern:
            return topic == pattern
        
        # Handle simple prefix patterns like "AAPL.*"
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic == prefix or topic.startswith(prefix + ".")
        
        # Handle simple suffix patterns like "*.ORDERBOOK"
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return topic.endswith("." + suffix)
        
        return False