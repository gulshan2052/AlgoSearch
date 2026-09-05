from typing import List

from pydantic import BaseModel

from app.interfaces.embedding import EmbeddingProvider
from app.interfaces.llm import LLMProvider
from app.interfaces.vector_store import VectorStore


class ProblemMatch(BaseModel):
    title: str
    url: str
    platform: str
    similarity_score: float
    summary: str


class SearchService:

    def __init__(
        self,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self.llm = llm
        self.embedder = embedder
        self.vector_store = vector_store

    async def find_similar(
        self, statement: str, constraints: str = "", top_k: int = 10
    ) -> List[ProblemMatch]:
        # Step 1: Strip lore using the identical prompt
        summary = await self.llm.generate_summary(statement, constraints)

        # Step 2: Generate embedding
        query_vector = await self.embedder.embed_text(summary)

        # Step 3: Query vector DB
        results = await self.vector_store.search(query_vector, top_k=top_k)

        # Step 4: Format response
        matches: List[ProblemMatch] = []
        for r in results:
            matches.append(
                ProblemMatch(
                    title=r.metadata.get("title", "Unknown"),
                    url=r.metadata.get("url", ""),
                    platform=r.metadata.get("platform", "Unknown"),
                    similarity_score=round(r.score, 4),
                    summary=r.document,
                )
            )
        return matches
