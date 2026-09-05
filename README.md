# Semantic Problem Matcher

A vector-search backend for competitive programming problems. It strips narrative/flavor text from problem statements into a canonical algorithmic summary via an LLM, embeds that summary, and stores it in a vector database so you can query "similar problems" by semantic meaning.

## Architecture

The backend is interface-driven (Dependency Inversion). Core business logic interacts only with abstract base interfaces for **LLM inference**, **Embeddings generation**, and **Vector storage**, so switching providers requires only changing a config key.

```
FastAPI Controllers
        |
    +---+---+
    v       v
Ingestion   Retrieval
    +---Service Abstractions (LLMProvider, Embedder, VectorDB)---+
        |                    |                      |
        v                    v                      v
 Ollama/OpenAI       Nomic/OpenAI           ChromaDB
   LLM               Embeddings              (vectors)
```

## Directory Structure

```
├── app/
│   ├── api/
│   │   ├── deps.py                 # Dependency injection wiring
│   │   └── v1/
│   │       ├── router.py
│   │       ├── ingestion.py        # Trigger batch ingestion
│   │       └── search.py           # Problem search endpoints
│   ├── core/
│   │   ├── config.py               # Pydantic settings & env management
│   │   └── prompts.py              # Canonical CP extraction prompt
│   ├── db/
│   │   ├── models.py               # SQLAlchemy SQLite models
│   │   └── session.py              # SQLAlchemy session factory
│   ├── interfaces/
│   │   ├── llm.py                  # Abstract LLM Interface
│   │   ├── embedding.py            # Abstract Embedding Interface
│   │   └── vector_store.py         # Abstract Vector Database Interface
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── ollama_llm.py
│   │   │   └── openai_llm.py       # Also works for OpenAI-compatible gateways
│   │   ├── embedding/
│   │   │   ├── ollama_embed.py
│   │   │   └── openai_embed.py
│   │   └── vector_store/
│   │       └── chroma_store.py
│   ├── services/
│   │   ├── ingestion_service.py    # Ingestion worker logic
│   │   └── search_service.py       # Query processing & top-k matching
│   └── main.py                     # FastAPI application factory
├── tests/
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the environment template and edit as needed:

```bash
cp .env.example .env
```

## Provider Configuration

Swap providers by setting flags in `.env`:

| Setting | Value | Purpose |
|---|---|---|
| `LLM_BACKEND` | `"ollama"` \| `"openai"` | Which LLM provider to use |
| `EMBEDDING_BACKEND` | `"ollama"` \| `"openai"` | Which embedding provider to use |

### Ollama (default)

```env
LLM_BACKEND=ollama
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=qwen2.5-coder
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Pull the models first:

```bash
ollama pull qwen2.5-coder
ollama pull nomic-embed-text
```

### OpenAI / Claude (via OpenAI-compatible gateway)

```env
LLM_BACKEND=openai
EMBEDDING_BACKEND=openai
OPENAI_API_KEY=sk-...
# Optional: set to an OpenAI-compatible endpoint
# e.g. vLLM, LM Studio, or a Claude-to-OpenAI proxy
OPENAI_BASE_URL=
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBED_MODEL=text-embedding-3-small
```

## Running

```bash
uvicorn app.main:app --reload --port 8000
```

1. **Populate SQLite**: An independent scraper inserts problems directly into `problems.db` with `status = 'PENDING'`.
2. **Start the backend** as above.
3. **Run the ingestion batch**:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingest/trigger?batch_size=100"
   ```

   The backend pulls unindexed items, summarizes them, generates embeddings, stores them in the vector database, and marks them `COMPLETED`.

4. **Search for similar problems**:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/search" \
     -H "Content-Type: application/json" \
     -d '{
       "statement": "Farmer John has N cows standing in a line...",
       "constraints": "N <= 10^5",
       "top_k": 5
     }'
   ```

   Returns the top matching problems with their URLs, algorithmic summaries, and similarity scores.

## Tests

```bash
pytest
```

## How It Works

- **Ingestion**: For each `PENDING` problem, an LLM produces a canonical algorithmic summary (stripping all lore/story), which is embedded and upserted into ChromaDB, then the problem's SQLite status is set to `COMPLETED`.
- **Search**: An input statement is summarized using the **identical** prompt (keeping both sides in the same embedding space), embedded, and used to query the vector DB for the top-k nearest neighbors.
