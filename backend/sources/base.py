from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class ResearchSource(ABC):
    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]: ...

    @abstractmethod
    async def fetch_content(self, url: str) -> str: ...
