from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel


class VectorRecord(BaseModel):
    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    document: str


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]
    document: str


class VectorStore(ABC):

    @abstractmethod
    async def upsert(self, records: List[VectorRecord]) -> None:
        """Inserts or updates vector records."""
        pass

    @abstractmethod
    async def search(
        self, query_vector: List[float], top_k: int = 10
    ) -> List[SearchResult]:
        """Searches for top_k nearest neighbors by cosine similarity."""
        pass
