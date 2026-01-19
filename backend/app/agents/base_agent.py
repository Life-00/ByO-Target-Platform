"""
Base Agent Class - All agents must inherit from this
Provides standard interface and utilities
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from datetime import datetime
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents
    
    Every agent must:
    1. Inherit from BaseAgent
    2. Implement execute() method
    3. Define agent_type in __init__
    4. Use InputSchema and OutputSchema
    """
    
    def __init__(self):
        """Initialize base agent properties"""
        self.agent_type: str = "base"
        self.agent_id: str = str(uuid4())
        self.created_at: datetime = datetime.utcnow()
        
        # Each agent should define their own system_prompt and persona
        # in their __init__ or from their prompt.py
        self.system_prompt: str = ""
        self.persona: Dict[str, Any] = {}
        
        # Logging
        self.logger = logging.getLogger(f"agents.{self.agent_type}")
    
    @abstractmethod
    async def execute(self, request: Any) -> Any:
        """
        Main execution method - must be implemented by subclass
        
        Args:
            request: InputSchema instance with user input
        
        Returns:
            OutputSchema instance with results
        
        Raises:
            Can raise exceptions - they will be caught by API layer
        """
        pass
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent metadata"""
        return {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "system_prompt": self.system_prompt[:100] + "..." if len(self.system_prompt) > 100 else self.system_prompt,
            "persona": self.persona.get("name", "Unknown")
        }
    
    def log_execution(self, session_id: str, status: str, message: str = None):
        """
        Log agent execution
        Useful for tracking what agents do
        """
        log_entry = {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "session_id": session_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.logger.info(f"Agent execution: {log_entry}")
        # Can be extended to save to database
        return log_entry
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate session exists (stub)
        Subclasses can override for actual database checks
        """
        if not session_id or len(session_id) == 0:
            self.logger.error("Invalid session_id")
            return False
        return True
    
    async def handle_error(self, error: Exception, context: str = None) -> Dict[str, Any]:
        """
        Standard error handling
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "agent_type": self.agent_type,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.error(f"Agent error: {error_info}")
        return error_info


class AgentRegistry:
    """
    Simple registry to manage all agents
    Used by API layer to call agents
    """
    
    _agents: Dict[str, type] = {}
    
    @classmethod
    def register(cls, agent_type: str, agent_class: type):
        """Register an agent"""
        cls._agents[agent_type] = agent_class
        logger.info(f"Registered agent: {agent_type}")
    
    @classmethod
    def get_agent(cls, agent_type: str) -> Optional[BaseAgent]:
        """Get agent instance by type"""
        agent_class = cls._agents.get(agent_type)
        if agent_class is None:
            logger.error(f"Agent not found: {agent_type}")
            return None
        return agent_class()
    
    @classmethod
    def list_agents(cls) -> Dict[str, type]:
        """List all registered agents"""
        return cls._agents.copy()


# Auto-register agents on import
def auto_register_agents():
    """
    Automatically register all agents
    Called after all agent modules are imported
    """
    try:
        from app.agents.general_chat.agent import GeneralChatAgent
        AgentRegistry.register("general_chat", GeneralChatAgent)
    except ImportError as e:
        logger.warning(f"Failed to register GeneralChatAgent: {e}")

    try:
        from app.agents.embedding_agent.agent import EmbeddingAgent
        AgentRegistry.register("embedding_agent", EmbeddingAgent)
    except ImportError as e:
        logger.warning(f"Failed to register EmbeddingAgent: {e}")
