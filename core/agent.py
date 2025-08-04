from abc import ABC, abstractmethod
from typing import Set, Dict, Any
from .message import Message, MessageBroker
from ..utils.logger import setup_logger
import logging


class Agent(ABC):
    """Abstract base class for all agents in the simulation"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.subscriptions: Set[str] = set()
        self.message_broker: MessageBroker = None
        self.kernel = None
        self.logger = setup_logger(f"Agent.{agent_id}")
    
    def set_message_broker(self, broker: MessageBroker):
        """Set the message broker for this agent"""
        self.message_broker = broker
        # Register this agent's message handler with the broker
        broker.register_agent_handler(self.agent_id, self.receive_message)
    
    def set_kernel(self, kernel):
        """Set reference to kernel for accessing current time"""
        self.kernel = kernel
    
    @abstractmethod
    def receive_message(self, message: Message):
        """Process incoming messages from subscribed topics"""
        pass
    
    def send_message(self, topic: str, payload: dict, timestamp: int = None):
        """Send message to a specific topic"""
        if self.message_broker is None:
            self.logger.error("Message broker not set for agent")
            raise RuntimeError("Message broker not set for agent")
        
        # Use current kernel time if timestamp not provided
        if timestamp is None:
            if self.kernel is not None:
                timestamp = self.kernel.get_current_time()
            else:
                timestamp = 0
        
        self.logger.debug(f"Sending message to topic {topic} with payload {payload}")
        
        message = Message(
            timestamp=timestamp,
            topic=topic,
            payload=payload,
            source_id=self.agent_id
        )
        self.message_broker.publish(message)
    
    def subscribe(self, topic_pattern: str):
        """Subscribe to messages from a topic or pattern"""
        if self.message_broker is None:
            self.logger.error("Message broker not set for agent")
            raise RuntimeError("Message broker not set for agent")
        
        self.logger.debug(f"Subscribing to topic pattern: {topic_pattern}")
        self.subscriptions.add(topic_pattern)
        self.message_broker.subscribe(self.agent_id, topic_pattern)
    
    def unsubscribe(self, topic_pattern: str):
        """Unsubscribe from messages from a topic or pattern"""
        if self.message_broker is None:
            self.logger.error("Message broker not set for agent")
            raise RuntimeError("Message broker not set for agent")
        
        self.logger.debug(f"Unsubscribing from topic pattern: {topic_pattern}")
        self.subscriptions.discard(topic_pattern)
        self.message_broker.unsubscribe(self.agent_id, topic_pattern)


class PassiveAgent(Agent):
    """Agent that only responds to messages (no scheduled wakeups)"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
    
    def receive_message(self, message: Message):
        """Process incoming messages - to be implemented by subclasses"""
        pass


class ActiveAgent(Agent):
    """Agent that can be scheduled for regular wakeups"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.scheduled_wakeups: Set[int] = set()
    
    def receive_message(self, message: Message):
        """Process incoming messages - to be implemented by subclasses"""
        pass
    
    def schedule_wakeup(self, timestamp: int):
        """Request to be woken up at a specific time"""
        self.scheduled_wakeups.add(timestamp)
        return timestamp
    
    def wakeup(self, current_time: int):
        """Called by kernel at each scheduled time step"""
        self.logger.debug(f"Waking up at time {current_time}")
        # Remove this wakeup time from scheduled wakeups
        self.scheduled_wakeups.discard(current_time)
        pass