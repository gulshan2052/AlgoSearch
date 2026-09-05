import logging

from sqlalchemy.orm import Session

from app.db.models import IngestionStatus, Problem
from app.interfaces.embedding import EmbeddingProvider
from app.interfaces.llm import LLMProvider
from app.interfaces.vector_store import VectorRecord, VectorStore

logger = logging.getLogger(__name__)


class IngestionService:

    def __init__(
        self,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self.llm = llm
        self.embedder = embedder
        self.vector_store = vector_store

    async def run_batch(self, db: Session, limit: int = 50) -> int:
        pending_problems = (
            db.query(Problem)
            .filter(Problem.status == IngestionStatus.PENDING)
            .limit(limit)
            .all()
        )

        processed_count = 0
        for problem in pending_problems:
            try:
                problem.status = IngestionStatus.PROCESSING
                db.commit()

                # Step 1: LLM canonical summarization
                summary = await self.llm.generate_summary(
                    problem_text=problem.statement,
                    constraints=problem.constraints or "",
                )

                # Step 2: Compute embedding vector
                vector = await self.embedder.embed_text(summary)

                # Step 3: Insert into vector database
                record = VectorRecord(
                    id=str(problem.id),
                    vector=vector,
                    metadata={
                        "platform": problem.platform,
                        "problem_id": problem.problem_id,
                        "title": problem.title,
                        "url": problem.url,
                    },
                    document=summary,
                )
                await self.vector_store.upsert([record])

                # Step 4: Mark completed in SQLite
                problem.summary = summary
                problem.status = IngestionStatus.COMPLETED
                problem.error_message = None
                processed_count += 1

            except Exception as exc:
                logger.error(
                    f"Failed to ingest problem {problem.id}: {str(exc)}"
                )
                problem.status = IngestionStatus.FAILED
                problem.error_message = str(exc)

            finally:
                db.commit()

        return processed_count
