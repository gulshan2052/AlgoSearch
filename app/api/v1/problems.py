import logging

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.db.session import engine
from app.services.import_service import (
    CatalogImportService,
    FileImportResult,
    ImportValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/problems/import", response_model=list[FileImportResult])
def import_problems(filename: str | None = None) -> list[FileImportResult]:
    """Merges scraped problems from the import directory into the catalog.

    By default every ``*.db`` file in ``settings.IMPORT_SOURCE_DIR`` is processed.
    Pass ``?filename=`` to target a single file. Each file must contain a
    ``problems`` table matching the schema in ``PROBLEMS_DB_GUIDE.md``. Rows are
    inserted keyed on the unique `url` column, so problems already present are
    skipped and existing rows are never overwritten. Source files are never
    modified or deleted.
    """

    try:
        results = CatalogImportService(engine).import_from_dir(
            settings.IMPORT_SOURCE_DIR, filename=filename
        )
    except ImportValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to import problems")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import problems: {exc}",
        )

    return results