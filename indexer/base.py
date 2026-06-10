from abc import ABC, abstractmethod
from pathlib import Path

class BaseIndexer(ABC):
    @abstractmethod
    def extensions(self) -> list[str]: ...

    @abstractmethod
    def parse_file(self, path: Path) -> tuple[list[dict], list[tuple[str, str]]]:
        """Returns (symbols, calls)."""
        ...
