from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embeds a single query string into a vector."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds multiple texts into vectors."""
        pass
