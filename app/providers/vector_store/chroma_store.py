from typing import List

import chromadb

from app.interfaces.vector_store import SearchResult, VectorRecord, VectorStore


class ChromaVectorStore(VectorStore):

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "problem_summaries",
    ):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    async def upsert(self, records: List[VectorRecord]) -> None:
        if not records:
            return
        self.collection.upsert(
            ids=[r.id for r in records],
            embeddings=[r.vector for r in records],
            metadatas=[r.metadata for r in records],
            documents=[r.document for r in records],
        )

    async def search(
        self, query_vector: List[float], top_k: int = 10
    ) -> List[SearchResult]:
        res = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

        results: List[SearchResult] = []
        ids = res["ids"][0]
        distances = res["distances"][0]
        metadatas = res["metadatas"][0]
        documents = res["documents"][0]

        for i in range(len(ids)):
            # Cosine distance to similarity conversion
            similarity = 1.0 - distances[i]
            results.append(
                SearchResult(
                    id=ids[i],
                    score=similarity,
                    metadata=metadatas[i],
                    document=documents[i],
                )
            )
        return results
