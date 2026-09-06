import logging

from app.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level, format=LOG_FORMAT)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = logging.getLogger().handlers
        logging.getLogger(name).propagate = False
        logging.getLogger(name).setLevel(level)

    for name in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
