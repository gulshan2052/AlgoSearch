import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.db.session import init_db

setup_logging()

logger = logging.getLogger(__name__)

MAX_BODY_LOG = 2000


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


class RequestLoggingMiddleware:
    """ASGI middleware that logs each request and its response without buffering the stream."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start = time.perf_counter()
        method = scope.get("method", "?")
        path = scope.get("path", "/")
        client = scope.get("client")
        client_host = client[0] if client else "unknown"

        logger.info("REQUEST  %s %s (client=%s)", method, path, client_host)

        status_holder: dict = {}
        body_chunks: list[bytes] = []

        async def capture_send(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message.get("status")
            elif message["type"] == "http.response.body":
                body = message.get("body")
                if body:
                    body_chunks.append(body)
            await send(message)

        await self.app(scope, receive, capture_send)

        duration_ms = (time.perf_counter() - start) * 1000
        body = b"".join(body_chunks)
        logger.info(
            "RESPONSE %s %s -> %s  [%.1f ms]  body=%s",
            method,
            path,
            status_holder.get("status", "?"),
            duration_ms,
            self._summarize_body(body),
        )

    @staticmethod
    def _summarize_body(body: bytes) -> str:
        text = body.decode("utf-8", errors="replace")
        return text if len(text) <= MAX_BODY_LOG else text[:MAX_BODY_LOG] + "…[truncated]"


app = FastAPI(
    title="Semantic Problem Matcher API",
    description="Vector search backend for competitive programming problems",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(api_router, prefix="/api/v1")