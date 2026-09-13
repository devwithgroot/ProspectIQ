from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Base interface that every ProspectIQ tool must implement.
    """

    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool and return its result.
        """
        pass