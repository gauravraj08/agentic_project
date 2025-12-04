from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """
    Standard Model Context Protocol (MCP) definition.
    All tools must inherit from this class.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """The specific logic the tool performs."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Returns the function signature for LLM tool calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {} # Subclasses should override this if needed
                }
            }
        }