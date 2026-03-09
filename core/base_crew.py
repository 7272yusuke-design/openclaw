from abc import ABC, abstractmethod
from typing import Any
from core.config import get_agent_llm

class NeoBaseCrew(ABC):
    """
    Base class for all Neo Crews.
    Provides standard LLM initialization and execution logging.
    """
    def __init__(self, name: str):
        self.name = name
        self.llm = get_agent_llm(name)

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        pass
