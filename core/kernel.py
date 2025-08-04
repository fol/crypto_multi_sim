import heapq
from typing import Dict, Set, List, Tuple
from .agent import Agent, ActiveAgent
from .message import MessageBroker
from utils.logger import setup_logger


class Kernel:
    """Kernel for managing time and scheduling events in the simulation"""
    
    def __init__(self):
        self.current_time = 0  # milliseconds since simulation start
        self.end_time = 0      # simulation end time
        self.event_queue = []  # priority queue: (timestamp, agent_id, event_type)
        self.message_broker = MessageBroker()
        self.agents: Dict[str, Agent] = {}
        self.agent_wakeups: Dict[int, Set[str]] = {}  # timestamp -> agent_ids
        self.logger = setup_logger("Kernel")
    
    def register_agent(self, agent: Agent):
        """Register an agent with the kernel"""
        self.agents[agent.agent_id] = agent
        agent.set_message_broker(self.message_broker)
        agent.set_kernel(self)
    
    def schedule_event(self, timestamp: int, agent_id: str, event_type: str = "wakeup"):
        """Schedule an agent wakeup or system event"""
        if timestamp < self.current_time:
            raise ValueError("Cannot schedule events in the past")
        
        heapq.heappush(self.event_queue, (timestamp, agent_id, event_type))
        
        # Track wakeups for active agents
        if event_type == "wakeup":
            if timestamp not in self.agent_wakeups:
                self.agent_wakeups[timestamp] = set()
            self.agent_wakeups[timestamp].add(agent_id)
    
    def run(self, end_time: int):
        """Run simulation until end_time"""
        self.logger.info(f"Starting simulation run for {end_time}ms")
        self.end_time = end_time
        self.current_time = 0
        
        # Process events until end time
        while self.current_time < self.end_time:
            if self.event_queue:
                # Get the next event timestamp
                next_timestamp = self.event_queue[0][0]
                
                # Make sure we don't go past end time
                if next_timestamp > self.end_time:
                    next_timestamp = self.end_time
                
                # Advance time to next event
                self.current_time = next_timestamp
                self.logger.debug(f"Processing events at timestamp {self.current_time}")
                
                # Process all events at this timestamp
                self._process_events_at_timestamp(next_timestamp)
            else:
                # No more events, advance to end time
                self.current_time = self.end_time
        
        # Deliver any remaining messages
        self.message_broker.deliver_messages(self.current_time)
        self.logger.info("Simulation run completed")
    
    def _process_events_at_timestamp(self, timestamp: int):
        """Process all events scheduled for a specific timestamp"""
        # Collect all events at this timestamp
        events_at_timestamp = []
        while self.event_queue and self.event_queue[0][0] == timestamp:
            event = heapq.heappop(self.event_queue)
            events_at_timestamp.append(event)
        
        # Deliver messages first
        self.message_broker.deliver_messages(timestamp)
        
        # Then wake up agents
        agent_wakeups = self.agent_wakeups.get(timestamp, set())
        for agent_id in agent_wakeups:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if isinstance(agent, ActiveAgent):
                    agent.wakeup(timestamp)
        
        # Clean up processed wakeups
        if timestamp in self.agent_wakeups:
            del self.agent_wakeups[timestamp]
    
    def get_current_time(self) -> int:
        """Get the current simulation time in milliseconds"""
        return self.current_time
    
    def schedule_agent_wakeup(self, agent_id: str, timestamp: int):
        """Schedule an agent to be woken up at a specific time"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not registered with kernel")
        
        self.schedule_event(timestamp, agent_id, "wakeup")