from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.providers.embedding.ollama_embed import OllamaEmbedding
from app.providers.embedding.openai_embed import OpenAIEmbedding
from app.providers.llm.ollama_llm import OllamaLLM
from app.providers.llm.openai_llm import OpenAILLM
from app.providers.vector_store.chroma_store import ChromaVectorStore
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService


def get_llm():
    if settings.LLM_BACKEND == "ollama":
        return OllamaLLM(
            base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_LLM_MODEL
        )
    return OpenAILLM(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_LLM_MODEL,
        base_url=settings.OPENAI_BASE_URL,
    )


def get_embedder():
    if settings.EMBEDDING_BACKEND == "ollama":
        return OllamaEmbedding(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_EMBED_MODEL,
        )
    return OpenAIEmbedding(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_EMBED_MODEL,
        base_url=settings.OPENAI_BASE_URL,
    )


def get_vector_store():
    return ChromaVectorStore(persist_dir=settings.CHROMA_PERSIST_DIR)


def get_ingestion_service(
    llm=Depends(get_llm),
    embedder=Depends(get_embedder),
    vector_store=Depends(get_vector_store),
):
    return IngestionService(
        llm=llm, embedder=embedder, vector_store=vector_store
    )


def get_search_service(
    llm=Depends(get_llm),
    embedder=Depends(get_embedder),
    vector_store=Depends(get_vector_store),
):
    return SearchService(llm=llm, embedder=embedder, vector_store=vector_store)
