"""The sole reporting port visible to a future scientific core."""
from abc import ABC, abstractmethod

from .events import RunEvent


class RunReporter(ABC):
    @abstractmethod
    def report(self, event: RunEvent) -> None:
        """Receive an event; delivery and persistence policies belong to adapters."""
        raise NotImplementedError
