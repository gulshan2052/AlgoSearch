import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_search_service
from app.services.search_service import ProblemMatch, SearchService

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    statement: str
    constraints: str = ""
    top_k: int = 10


@router.post("/search", response_model=list[ProblemMatch])
async def search_similar_problems(
    payload: SearchRequest,
    search_service: SearchService = Depends(get_search_service),
):
    """Summarizes input problem statement, removes lore, and returns the top matching indexed problems."""
    logger.info("Search request received: top_k=%d", payload.top_k)
    result = await search_service.find_similar(
        statement=payload.statement,
        constraints=payload.constraints,
        top_k=payload.top_k,
    )
    return result
