from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SQLITE_URL: str = "sqlite:///./problems.db"
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # Provider Selection: "ollama" | "openai"
    LLM_BACKEND: str = "ollama"
    EMBEDDING_BACKEND: str = "ollama"

    # Ollama Config
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5-coder"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # OpenAI / Claude Config
    OPENAI_API_KEY: str = "sk-..."
    OPENAI_BASE_URL: str | None = None
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"


settings = Settings()
