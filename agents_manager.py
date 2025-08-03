from typing import AsyncGenerator, List, Optional
from agent_event import AgentEvent
from agents import Agent
from exchange import Exchange

class AgentsManager:
    """Manages a collection of agents and their events."""
    
    agents: List[Agent]
    
    def __init__(self, exchange: Optional[Exchange] = None):
        """Initialize the AgentsManager.
        
        Args:
            exchange: The exchange instance that agents will interact with.
        """
        self.agents = []
        self.exchange = exchange
    
    def add_agent(self, agent: Agent) -> None:
        """Add an agent to the manager.
        
        Args:
            agent: The agent to add.
        """
        self.agents.append(agent)
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent by ID.
        
        Args:
            agent_id: The ID of the agent to remove.
            
        Returns:
            True if the agent was found and removed, False otherwise.
        """
        for i, agent in enumerate(self.agents):
            if agent.id == agent_id:
                self.agents.pop(i)
                return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id: The ID of the agent to retrieve.
            
        Returns:
            The agent if found, None otherwise.
        """
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None
    
    async def run(self) -> AsyncGenerator[AgentEvent, None]:
        """Run all agents and yield their events.
        
        Yields:
            Events from all managed agents.
        """
        # This would collect and yield events from all agents
        # For now, it's a placeholder implementation
        for agent in self.agents:
            async for event in agent.generate_events():
                yield event
