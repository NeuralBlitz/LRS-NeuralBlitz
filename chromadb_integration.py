"""
ChromaDB Vector Database Integration
Purpose: Local embeddings storage and retrieval
Author: NeuralBlitz Research Team
"""

import os
import logging
from typing import List, Dict, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import chromadb
try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not installed. Run: pip install chromadb")
    CHROMADB_AVAILABLE = False

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("NumPy not installed. Some features may be limited.")
    NUMPY_AVAILABLE = False


@dataclass
class Document:
    """Represents a document with embedding and metadata."""

    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class ChromaDBIntegration:
    """
    ChromaDB vector database integration for local embeddings.

    Features:
    - Local/embedded operation (no external server needed)
    - Persistent or in-memory storage
    - Automatic embedding generation (optional)
    - CRUD operations on documents
    - Metadata filtering
    - Multiple distance metrics (cosine, L2, inner product)
    - Collection-based organization
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Callable] = None,
        distance_metric: str = "cosine",
    ):
        """
        Initialize ChromaDB integration.

        Args:
            persist_directory: Path for persistent storage (None = in-memory)
            embedding_function: Optional function to generate embeddings
            distance_metric: Distance function (cosine, l2, ip)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not installed. Run: pip install chromadb")

        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.distance_metric = distance_metric
        self.client = None
        self.active_collection = None
        self.collection_name = None

    def connect(self) -> bool:
        """Initialize connection to ChromaDB."""
        try:
            if self.persist_directory:
                # Persistent client
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False),
                )
                logger.info(
                    f"✓ Connected to ChromaDB (persistent: {self.persist_directory})"
                )
            else:
                # Ephemeral/in-memory client
                self.client = chromadb.EphemeralClient()
                logger.info("✓ Connected to ChromaDB (in-memory)")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            return False

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Create a new collection.

        Args:
            name: Collection name
            metadata: Optional collection metadata

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Check if collection exists
            try:
                existing = self.client.get_collection(name)
                logger.info(f"Collection '{name}' already exists")
                self.active_collection = existing
                self.collection_name = name
                return True
            except:
                pass

            # Create new collection
            collection_metadata = metadata or {}
            collection_metadata["hnsw:space"] = self.distance_metric
            collection_metadata["created_at"] = datetime.utcnow().isoformat()

            self.active_collection = self.client.create_collection(
                name=name,
                metadata=collection_metadata,
                embedding_function=self.embedding_function,
            )
            self.collection_name = name

            logger.info(f"✓ Created collection: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    def use_collection(self, name: str) -> bool:
        """Switch to an existing collection."""
        if not self.client:
            raise RuntimeError("Not connected.")

        try:
            self.active_collection = self.client.get_collection(
                name=name, embedding_function=self.embedding_function
            )
            self.collection_name = name
            logger.info(f"✓ Using collection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to use collection: {e}")
            return False

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if not self.client:
            raise RuntimeError("Not connected.")

        try:
            self.client.delete_collection(name)

            if self.collection_name == name:
                self.active_collection = None
                self.collection_name = None

            logger.info(f"✓ Deleted collection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    def list_collections(self) -> List[str]:
        """List all collections."""
        if not self.client:
            raise RuntimeError("Not connected.")

        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    # ==================== CRUD OPERATIONS ====================

    def create(
        self, documents: List[Document], batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        CREATE: Insert documents into the collection.

        Args:
            documents: List of Document objects
            batch_size: Batch size for insertion

        Returns:
            Dict with operation results
        """
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        results = {"success": 0, "failed": 0, "errors": []}

        try:
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]

                ids = []
                texts = []
                embeddings = []
                metadatas = []

                for doc in batch:
                    try:
                        # Use provided ID or generate one
                        doc_id = doc.id or str(uuid.uuid4())
                        ids.append(doc_id)
                        texts.append(doc.text)

                        # Use provided embedding or None (ChromaDB will generate if function provided)
                        if doc.embedding:
                            embeddings.append(doc.embedding)

                        # Prepare metadata
                        metadata = doc.metadata.copy()
                        metadata["created_at"] = doc.created_at
                        metadatas.append(metadata)

                        results["success"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(
                            {"doc": doc.text[:50], "error": str(e)}
                        )

                # Add to collection
                if embeddings and len(embeddings) == len(ids):
                    # All documents have embeddings
                    self.active_collection.add(
                        ids=ids,
                        documents=texts,
                        embeddings=embeddings,
                        metadatas=metadatas,
                    )
                else:
                    # Let ChromaDB generate embeddings
                    self.active_collection.add(
                        ids=ids, documents=texts, metadatas=metadatas
                    )

                logger.info(f"✓ Added batch: {len(ids)} documents")

            return results

        except Exception as e:
            logger.error(f"Create operation failed: {e}")
            results["errors"].append(str(e))
            return results

    def read(
        self,
        ids: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Document]:
        """
        READ: Retrieve documents by ID or filters.

        Args:
            ids: List of document IDs
            filters: Metadata filters
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Document objects
        """
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        documents = []

        try:
            if ids:
                # Fetch specific documents
                result = self.active_collection.get(
                    ids=ids, include=["documents", "metadatas", "embeddings"]
                )
            elif filters:
                # Query with filters
                result = self.active_collection.get(
                    where=filters,
                    limit=limit,
                    offset=offset,
                    include=["documents", "metadatas", "embeddings"],
                )
            else:
                # Get all (up to limit)
                result = self.active_collection.get(
                    limit=limit,
                    offset=offset,
                    include=["documents", "metadatas", "embeddings"],
                )

            # Parse results
            for i, doc_id in enumerate(result.get("ids", [])):
                doc = Document(
                    id=doc_id,
                    text=result.get("documents", [])[i]
                    if result.get("documents")
                    else "",
                    embedding=result.get("embeddings", [])[i]
                    if result.get("embeddings")
                    else None,
                    metadata=result.get("metadatas", [])[i]
                    if result.get("metadatas")
                    else {},
                )
                documents.append(doc)

            logger.info(f"✓ Retrieved {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Read operation failed: {e}")
            return []

    def update(self, documents: List[Document]) -> Dict[str, Any]:
        """
        UPDATE: Modify existing documents.

        ChromaDB uses upsert semantics - creates if not exists, updates if exists.

        Args:
            documents: List of Document objects

        Returns:
            Dict with operation results
        """
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        results = {"success": 0, "failed": 0, "errors": []}

        try:
            ids = []
            texts = []
            embeddings = []
            metadatas = []

            for doc in documents:
                if not doc.id:
                    results["failed"] += 1
                    results["errors"].append(
                        {"text": doc.text[:50], "error": "No ID provided"}
                    )
                    continue

                ids.append(doc.id)
                texts.append(doc.text)

                if doc.embedding:
                    embeddings.append(doc.embedding)

                metadata = doc.metadata.copy()
                metadata["updated_at"] = datetime.utcnow().isoformat()
                metadatas.append(metadata)

                results["success"] += 1

            # Use upsert (update or insert)
            if embeddings and len(embeddings) == len(ids):
                self.active_collection.upsert(
                    ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas
                )
            else:
                self.active_collection.upsert(
                    ids=ids, documents=texts, metadatas=metadatas
                )

            logger.info(f"✓ Updated {results['success']} documents")
            return results

        except Exception as e:
            logger.error(f"Update operation failed: {e}")
            results["errors"].append(str(e))
            return results

    def delete(
        self, ids: Optional[List[str]] = None, filters: Optional[Dict] = None
    ) -> bool:
        """
        DELETE: Remove documents by ID or filter.

        Args:
            ids: List of document IDs
            filters: Metadata filter for bulk delete

        Returns:
            True if successful
        """
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        try:
            if ids:
                self.active_collection.delete(ids=ids)
                logger.info(f"✓ Deleted {len(ids)} documents")

            elif filters:
                self.active_collection.delete(where=filters)
                logger.info(f"✓ Deleted documents matching filter: {filters}")

            else:
                logger.warning("No delete criteria specified")
                return False

            return True

        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return False

    # ==================== SEMANTIC SEARCH ====================

    def query(
        self,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10,
        filters: Optional[Dict] = None,
        include_embeddings: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search by text or embedding.

        Args:
            query_text: Text query (will be embedded)
            query_embedding: Query vector
            top_k: Number of results
            filters: Metadata filters
            include_embeddings: Include vector in results

        Returns:
            List of results with similarity scores
        """
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        try:
            include = ["documents", "metadatas", "distances"]
            if include_embeddings:
                include.append("embeddings")

            if query_embedding:
                # Search by vector
                results = self.active_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=filters,
                    include=include,
                )
            elif query_text:
                # Search by text (ChromaDB will embed)
                results = self.active_collection.query(
                    query_texts=[query_text],
                    n_results=top_k,
                    where=filters,
                    include=include,
                )
            else:
                logger.error("Either query_text or query_embedding required")
                return []

            # Parse results
            output = []
            if results.get("ids") and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    result = {
                        "id": doc_id,
                        "text": results["documents"][0][i]
                        if results.get("documents")
                        else "",
                        "metadata": results["metadatas"][0][i]
                        if results.get("metadatas")
                        else {},
                        "distance": results["distances"][0][i]
                        if results.get("distances")
                        else None,
                    }
                    if include_embeddings and results.get("embeddings"):
                        result["embedding"] = results["embeddings"][0][i]
                    output.append(result)

            logger.info(f"✓ Query returned {len(output)} results")
            return output

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def search_by_vector(
        self, vector: List[float], top_k: int = 10, filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Convenience method for vector-only search."""
        return self.query(query_embedding=vector, top_k=top_k, filters=filters)

    def search_by_text(
        self, text: str, top_k: int = 10, filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Convenience method for text search."""
        return self.query(query_text=text, top_k=top_k, filters=filters)

    # ==================== EMBEDDING OPERATIONS ====================

    def generate_embeddings(
        self, texts: List[str], model: str = "all-MiniLM-L6-v2"
    ) -> List[List[float]]:
        """
        Generate embeddings for texts using ChromaDB's default embedding function.

        Args:
            texts: List of text strings
            model: Model name (if using sentence-transformers)

        Returns:
            List of embedding vectors
        """
        try:
            from chromadb.utils import embedding_functions

            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model
            )
            embeddings = ef(texts)
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []

    # ==================== UTILITY METHODS ====================

    def count(self) -> int:
        """Get total document count in collection."""
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        try:
            return self.active_collection.count()
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0

    def peek(self, limit: int = 5) -> List[Document]:
        """Peek at first N documents in collection."""
        return self.read(limit=limit)

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the active collection."""
        if not self.active_collection:
            raise RuntimeError("No collection selected.")

        try:
            return {
                "name": self.collection_name,
                "count": self.count(),
                "metadata": self.active_collection.metadata,
                "distance_metric": self.distance_metric,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}

    def export_collection(self, filepath: str) -> bool:
        """
        Export collection to JSON file.

        Args:
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            import json

            documents = self.read(limit=10000)  # Export up to 10k docs
            export_data = {
                "collection_name": self.collection_name,
                "export_date": datetime.utcnow().isoformat(),
                "documents": [
                    {
                        "id": doc.id,
                        "text": doc.text,
                        "embedding": doc.embedding,
                        "metadata": doc.metadata,
                        "created_at": doc.created_at,
                    }
                    for doc in documents
                ],
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"✓ Exported {len(documents)} documents to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def import_collection(self, filepath: str) -> bool:
        """
        Import collection from JSON file.

        Args:
            filepath: Input file path

        Returns:
            True if successful
        """
        try:
            import json

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            documents = [
                Document(
                    id=doc["id"],
                    text=doc["text"],
                    embedding=doc.get("embedding"),
                    metadata=doc.get("metadata", {}),
                    created_at=doc.get("created_at"),
                )
                for doc in data.get("documents", [])
            ]

            result = self.create(documents)
            logger.info(f"✓ Imported {result['success']} documents from {filepath}")
            return result["failed"] == 0

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False


# ==================== EXAMPLE USAGE ====================


def example_usage():
    """Demonstrate ChromaDB CRUD operations."""
    print("=" * 60)
    print("CHROMADB LOCAL EMBEDDINGS - EXAMPLE USAGE")
    print("=" * 60)

    try:
        # Initialize with persistent storage
        chroma = ChromaDBIntegration(
            persist_directory="./chroma_data", distance_metric="cosine"
        )

        # Connect
        if not chroma.connect():
            print("❌ Failed to connect")
            return

        # Create collection
        print("\n--- CREATE COLLECTION ---")
        chroma.create_collection(
            "documents", metadata={"description": "Document storage"}
        )

        # CREATE: Insert documents
        print("\n--- CREATE ---")
        documents = [
            Document(
                id="doc-001",
                text="The quick brown fox jumps over the lazy dog",
                embedding=None,  # ChromaDB will generate if embedding_function provided
                metadata={"category": "animals", "source": "example"},
            ),
            Document(
                id="doc-002",
                text="Machine learning is a subset of artificial intelligence",
                metadata={"category": "technology", "source": "wiki"},
            ),
            Document(
                id="doc-003",
                text="Python is a programming language",
                metadata={"category": "technology", "source": "docs"},
            ),
            Document(
                id="doc-004",
                text="The cat sat on the mat",
                metadata={"category": "animals", "source": "story"},
            ),
        ]

        # For demo purposes, create simple embeddings manually
        # In real use, you'd use an embedding function
        for i, doc in enumerate(documents):
            # Simple synthetic embedding for demo
            doc.embedding = [0.1 * (i + 1)] * 384

        result = chroma.create(documents)
        print(f"Created: {result['success']} succeeded, {result['failed']} failed")

        # READ: Fetch by ID
        print("\n--- READ (by ID) ---")
        records = chroma.read(ids=["doc-001", "doc-002"])
        for r in records:
            print(f"  {r.id}: {r.text[:40]}...")

        # READ: Filter by metadata
        print("\n--- READ (filtered) ---")
        filtered = chroma.read(filters={"category": "technology"})
        print(f"Technology docs: {len(filtered)}")
        for r in filtered:
            print(f"  - {r.text[:50]}...")

        # UPDATE: Modify document
        print("\n--- UPDATE ---")
        updated_doc = Document(
            id="doc-001",
            text="The quick brown fox jumps over the lazy dog (updated)",
            embedding=[0.11] * 384,
            metadata={"category": "animals", "source": "example", "updated": True},
        )
        result = chroma.update([updated_doc])
        print(f"Updated: {result['success']} documents")

        # QUERY: Semantic search
        print("\n--- QUERY (semantic search) ---")
        query_vector = [0.15] * 384  # Similar to technology docs
        results = chroma.search_by_vector(query_vector, top_k=3)
        for r in results:
            print(f"  {r['id']} (distance: {r['distance']:.4f}): {r['text'][:40]}...")

        # QUERY: By text (requires embedding function)
        # results = chroma.search_by_text("artificial intelligence", top_k=3)

        # DELETE
        print("\n--- DELETE ---")
        deleted = chroma.delete(ids=["doc-004"])
        print(f"Deleted: {deleted}")

        # STATS
        print("\n--- COLLECTION STATS ---")
        info = chroma.get_collection_info()
        print(f"Collection: {info.get('name')}")
        print(f"Document count: {info.get('count')}")
        print(f"Distance metric: {info.get('distance_metric')}")

        # List collections
        print("\n--- LIST COLLECTIONS ---")
        collections = chroma.list_collections()
        print(f"Available collections: {collections}")

        print("\n✓ Example completed successfully!")
        print(f"   Data persisted to: ./chroma_data")

    except ImportError as e:
        print(f"\n⚠️  {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
