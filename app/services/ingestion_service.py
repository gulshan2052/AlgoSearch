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

        logger.info(
            "Ingestion batch started: %d pending problem(s) found (limit=%d)",
            len(pending_problems),
            limit,
        )

        processed_count = 0
        failed_count = 0
        for index, problem in enumerate(pending_problems, start=1):
            stage = "initializing"
            problem_context = (
                f"[{index}/{len(pending_problems)}] id={problem.id} "
                f"problem_id={problem.problem_id} platform={problem.platform} "
                f"title={problem.title!r}"
            )
            try:
                stage = "marking PROCESSING"
                problem.status = IngestionStatus.PROCESSING
                db.commit()
                logger.info("PROBLEM %s: stage=PROCESSING (state persisted)", problem_context)

                # Step 1: LLM canonical summarization
                stage = "LLM summarization"
                logger.info("PROBLEM %s: stage=LLM summarization (started)", problem_context)
                summary = await self.llm.generate_summary(
                    problem_text=problem.statement,
                    constraints=problem.constraints or "",
                )
                logger.info("PROBLEM %s: stage=LLM summarization (done)", problem_context)

                # Step 2: Compute embedding vector
                stage = "embedding"
                logger.info("PROBLEM %s: stage=embedding (started)", problem_context)
                vector = await self.embedder.embed_text(summary)
                logger.info(
                    "PROBLEM %s: stage=embedding (done, dim=%d)",
                    problem_context,
                    len(vector),
                )

                # Step 3: Insert into vector database
                stage = "vector upsert"
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
                logger.info("PROBLEM %s: stage=vector upsert (done)", problem_context)

                # Step 4: Mark completed in SQLite
                stage = "marking COMPLETED"
                problem.summary = summary
                problem.status = IngestionStatus.COMPLETED
                problem.error_message = None
                processed_count += 1
                logger.info("PROBLEM %s: stage=COMPLETED", problem_context)

            except Exception as exc:
                failed_count += 1
                logger.error(
                    "PROBLEM %s: FAILED at stage=%r: %s",
                    problem_context,
                    stage,
                    exc,
                    exc_info=True,
                )
                problem.status = IngestionStatus.FAILED
                problem.error_message = str(exc)

            finally:
                db.commit()

        logger.info(
            "Ingestion batch finished: processed=%d failed=%d total_attempted=%d",
            processed_count,
            failed_count,
            len(pending_problems),
        )
        return processed_count
