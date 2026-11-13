import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

logger = logging.getLogger("ruby.retrieval.chroma")


class ChromaStore:
    """
    Persistent ChromaDB vector store for document chunks.
    Manages indexing, querying, deletion, and schema transitions.
    """

    COLLECTION_NAME = "ruby_chunks"

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = str((persist_dir or settings.chroma_dir).resolve() if isinstance(persist_dir or settings.chroma_dir, type(settings.chroma_dir)) else persist_dir or settings.chroma_dir)
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
            )
        return self._client

    def get_collection(self):
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    @staticmethod
    def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
        """ChromaDB metadata only accepts str, int, float, bool. Convert None and complex objects."""
        clean: Dict[str, Any] = {}
        for k, v in meta.items():
            if v is None:
                clean[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean

    def add_chunks(
        self,
        chunk_ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Upsert a batch of chunks with embeddings and metadata into ChromaDB."""
        if not chunk_ids:
            return

        collection = self.get_collection()
        clean_metas = [self._sanitize_metadata(m) for m in metadatas]

        # Chroma upsert is idempotent
        collection.upsert(
            ids=chunk_ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=clean_metas,
        )
        logger.info("ChromaDB: Indexed %d chunks in collection '%s'", len(chunk_ids), self.COLLECTION_NAME)

    def query_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query vector collection using cosine similarity.
        Returns matched chunks ranked by similarity score descending.
        """
        collection = self.get_collection()
        total_items = collection.count()
        if total_items == 0:
            return []

        n_results = min(top_k, total_items)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where_filter:
            kwargs["where"] = where_filter

        try:
            results = collection.query(**kwargs)
        except Exception as e:
            logger.warning("ChromaDB query failed with filter %s: %s", where_filter, e)
            return []

        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else [0.0] * len(ids)
        documents = results.get("documents", [[]])[0] if "documents" in results and results["documents"] else [""] * len(ids)
        metas = results.get("metadatas", [[]])[0] if "metadatas" in results and results["metadatas"] else [{}] * len(ids)

        items: List[Dict[str, Any]] = []
        for i, c_id in enumerate(ids):
            dist = float(distances[i]) if i < len(distances) else 1.0
            # Cosine distance: 0 is identical, 2 is opposite.
            # Convert to similarity: similarity = max(0.0, 1.0 - (dist / 2.0))
            sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            items.append({
                "chunk_id": c_id,
                "content": documents[i] if i < len(documents) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dist,
                "similarity": sim,
            })

        # Rank by similarity descending
        items.sort(key=lambda x: x["similarity"], reverse=True)
        return items

    def delete_by_document(self, document_id: str) -> None:
        """Remove all chunks belonging to a document from ChromaDB."""
        collection = self.get_collection()
        try:
            collection.delete(where={"document_id": document_id})
            logger.info("ChromaDB: Deleted chunks for document %s", document_id)
        except Exception as e:
            logger.warning("ChromaDB delete by document failed: %s", e)

    def delete_by_ids(self, chunk_ids: List[str]) -> None:
        """Remove specified chunk IDs from ChromaDB."""
        if not chunk_ids:
            return
        collection = self.get_collection()
        try:
            collection.delete(ids=chunk_ids)
            logger.info("ChromaDB: Deleted %d chunks by ID", len(chunk_ids))
        except Exception as e:
            logger.warning("ChromaDB delete by IDs failed: %s", e)

    def rebuild_collection(self) -> None:
        """Drop existing collection and re-create a clean index."""
        client = self._get_client()
        try:
            client.delete_collection(name=self.COLLECTION_NAME)
        except Exception:
            pass
        self._collection = client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB: Collection '%s' rebuilt cleanly.", self.COLLECTION_NAME)

    def count(self) -> int:
        """Return total number of vectors in collection."""
        try:
            return self.get_collection().count()
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collection_name": self.COLLECTION_NAME,
            "persist_dir": self.persist_dir,
            "total_chunks": self.count(),
        }


chroma_store = ChromaStore()
