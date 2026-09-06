import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.deps import get_ingestion_service
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestTriggerResponse(BaseModel):
    message: str
    status: str


@router.post("/ingest/trigger", response_model=IngestTriggerResponse)
def trigger_batch_ingestion(
    background_tasks: BackgroundTasks,
    batch_size: int = 50,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """Triggers an asynchronous worker batch to ingest pending problems from SQLite into the vector database."""

    async def worker():
        logger.info("Ingestion worker started (batch_size=%d)", batch_size)
        with SessionLocal() as db:
            processed = await ingestion_service.run_batch(db, limit=batch_size)
        logger.info("Ingestion worker finished (processed=%d)", processed)

    background_tasks.add_task(worker)
    logger.info("Ingestion trigger accepted (batch_size=%d)", batch_size)
    return IngestTriggerResponse(
        message=f"Ingestion batch job for {batch_size} problems scheduled.",
        status="ACCEPTED",
    )
