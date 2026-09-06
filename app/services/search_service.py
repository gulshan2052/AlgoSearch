import logging
import time
from typing import List

from pydantic import BaseModel

from app.interfaces.embedding import EmbeddingProvider
from app.interfaces.llm import LLMProvider
from app.interfaces.vector_store import VectorStore

logger = logging.getLogger(__name__)


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
        logger.info(
            "Search started: statement_len=%d constraints_len=%d top_k=%d",
            len(statement),
            len(constraints),
            top_k,
        )

        # Step 1: Strip lore using the identical prompt
        start = time.perf_counter()
        summary = await self.llm.generate_summary(statement, constraints)
        logger.info(
            "Search: LLM summary done (%.1f ms, summary_len=%d)",
            (time.perf_counter() - start) * 1000,
            len(summary),
        )

        # Step 2: Generate embedding
        start = time.perf_counter()
        query_vector = await self.embedder.embed_text(summary)
        logger.info(
            "Search: embedding done (%.1f ms, dim=%d)",
            (time.perf_counter() - start) * 1000,
            len(query_vector),
        )

        # Step 3: Query vector DB
        start = time.perf_counter()
        results = await self.vector_store.search(query_vector, top_k=top_k)
        logger.info(
            "Search: vector query done (%.1f ms, raw_results=%d)",
            (time.perf_counter() - start) * 1000,
            len(results),
        )

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
        logger.info(
            "Search finished: %d match(es) -> %s",
            len(matches),
            [m.title for m in matches],
        )
        return matches
