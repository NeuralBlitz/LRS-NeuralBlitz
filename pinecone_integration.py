"""
Pinecone Vector Database Integration
Purpose: Semantic memory storage and retrieval at scale
Author: NeuralBlitz Research Team
"""

import os
import logging
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import pinecone
try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    logger.warning("Pinecone client not installed. Run: pip install pinecone-client")
    PINECONE_AVAILABLE = False

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    logger.warning("NumPy not installed. Some features may be limited.")
    NUMPY_AVAILABLE = False


@dataclass
class VectorRecord:
    """Represents a vector record with metadata."""

    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class PineconeIntegration:
    """
    Pinecone vector database integration for semantic memory.

    Features:
    - CRUD operations on vector records
    - Metadata-based filtering
    - Batch operations for efficiency
    - Namespace isolation
    - Hybrid search capabilities
    """

    def __init__(self, api_key: Optional[str] = None, environment: str = "us-east-1"):
        """
        Initialize Pinecone integration.

        Args:
            api_key: Pinecone API key (or from PINECONE_API_KEY env var)
            environment: Pinecone environment (default: us-east-1)
        """
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone client not installed. Run: pip install pinecone-client"
            )

        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Pinecone API key required. Set PINECONE_API_KEY env var or pass to constructor."
            )

        self.environment = environment
        self.pc = None
        self.index = None
        self.index_name = None
        self.dimension = None

    def connect(self) -> bool:
        """Initialize connection to Pinecone."""
        try:
            self.pc = Pinecone(api_key=self.api_key)
            logger.info("✓ Connected to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            return False

    def create_index(
        self,
        name: str,
        dimension: int = 1536,
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1",
    ) -> bool:
        """
        Create a new Pinecone index.

        Args:
            name: Index name
            dimension: Vector dimension (default: 1536 for OpenAI embeddings)
            metric: Distance metric (cosine, euclidean, dotproduct)
            cloud: Cloud provider (aws, gcp, azure)
            region: Cloud region
        """
        if not self.pc:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Check if index already exists
            if name in self.pc.list_indexes().names():
                logger.info(f"Index '{name}' already exists")
                self.index_name = name
                self.index = self.pc.Index(name)
                self.dimension = dimension
                return True

            # Create new index
            self.pc.create_index(
                name=name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region),
            )

            self.index_name = name
            self.index = self.pc.Index(name)
            self.dimension = dimension
            logger.info(f"✓ Created index: {name} ({dimension}d, {metric})")
            return True

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def use_index(self, name: str) -> bool:
        """Switch to an existing index."""
        if not self.pc:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            self.index = self.pc.Index(name)
            self.index_name = name

            # Get index stats to determine dimension
            stats = self.index.describe_index_stats()
            self.dimension = stats.dimension

            logger.info(f"✓ Using index: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to use index: {e}")
            return False

    # ==================== CRUD OPERATIONS ====================

    def create(
        self, vectors: List[VectorRecord], namespace: str = "", batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        CREATE: Insert vectors into Pinecone.

        Args:
            vectors: List of VectorRecord objects
            namespace: Optional namespace for multi-tenancy
            batch_size: Number of vectors per batch

        Returns:
            Dict with operation results
        """
        if not self.index:
            raise RuntimeError(
                "No index selected. Call create_index() or use_index() first."
            )

        results = {"success": 0, "failed": 0, "errors": []}

        try:
            # Process in batches
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]

                # Prepare vectors for upsert
                upsert_data = []
                for record in batch:
                    # Validate dimension
                    if len(record.vector) != self.dimension:
                        error_msg = f"Vector dimension mismatch: {len(record.vector)} != {self.dimension}"
                        results["failed"] += 1
                        results["errors"].append({"id": record.id, "error": error_msg})
                        continue

                    # Add timestamp to metadata
                    metadata = record.metadata.copy()
                    metadata["created_at"] = record.created_at

                    upsert_data.append(
                        {"id": record.id, "values": record.vector, "metadata": metadata}
                    )

                if upsert_data:
                    # Upsert to Pinecone
                    self.index.upsert(vectors=upsert_data, namespace=namespace)
                    results["success"] += len(upsert_data)
                    logger.info(f"✓ Upserted batch: {len(upsert_data)} vectors")

            return results

        except Exception as e:
            logger.error(f"Create operation failed: {e}")
            results["errors"].append(str(e))
            return results

    def read(
        self,
        ids: Optional[List[str]] = None,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        top_k: int = 10,
    ) -> List[VectorRecord]:
        """
        READ: Retrieve vectors by ID or metadata filter.

        Args:
            ids: List of vector IDs to fetch
            namespace: Namespace to search
            filter_dict: Metadata filter (e.g., {"category": "science"})
            top_k: Maximum results for filter-based queries

        Returns:
            List of VectorRecord objects
        """
        if not self.index:
            raise RuntimeError("No index selected.")

        records = []

        try:
            # Fetch by IDs
            if ids:
                response = self.index.fetch(ids=ids, namespace=namespace)

                for vid, data in response.vectors.items():
                    record = VectorRecord(
                        id=vid,
                        vector=data.values,
                        metadata=data.metadata or {},
                        created_at=data.metadata.get("created_at")
                        if data.metadata
                        else None,
                    )
                    records.append(record)

            # Query by filter (requires dummy vector)
            elif filter_dict:
                # Create a zero vector for filter-only query
                dummy_vector = [0.0] * self.dimension

                response = self.index.query(
                    vector=dummy_vector,
                    filter=filter_dict,
                    top_k=top_k,
                    namespace=namespace,
                    include_metadata=True,
                )

                for match in response.matches:
                    record = VectorRecord(
                        id=match.id,
                        vector=match.values if hasattr(match, "values") else [],
                        metadata=match.metadata or {},
                        created_at=match.metadata.get("created_at")
                        if match.metadata
                        else None,
                    )
                    records.append(record)

            logger.info(f"✓ Retrieved {len(records)} records")
            return records

        except Exception as e:
            logger.error(f"Read operation failed: {e}")
            return []

    def update(
        self, records: List[VectorRecord], namespace: str = "", batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        UPDATE: Update existing vectors.

        In Pinecone, update is done via upsert (same as create).

        Args:
            records: List of VectorRecord objects with updated values
            namespace: Namespace
            batch_size: Batch size for operations

        Returns:
            Dict with operation results
        """
        # Pinecone uses upsert for both create and update
        logger.info("Updating vectors (using upsert)...")

        # Add updated timestamp
        for record in records:
            record.metadata["updated_at"] = datetime.utcnow().isoformat()

        return self.create(records, namespace, batch_size)

    def delete(
        self,
        ids: Optional[List[str]] = None,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        delete_all: bool = False,
    ) -> bool:
        """
        DELETE: Remove vectors by ID or filter.

        Args:
            ids: List of IDs to delete
            namespace: Namespace
            filter_dict: Metadata filter for bulk delete
            delete_all: Delete all vectors in namespace (use with caution!)

        Returns:
            True if successful
        """
        if not self.index:
            raise RuntimeError("No index selected.")

        try:
            if delete_all:
                self.index.delete(delete_all=True, namespace=namespace)
                logger.warning(f"⚠ Deleted ALL vectors in namespace: {namespace}")

            elif ids:
                self.index.delete(ids=ids, namespace=namespace)
                logger.info(f"✓ Deleted {len(ids)} vectors")

            elif filter_dict:
                # Delete by metadata filter
                self.index.delete(filter=filter_dict, namespace=namespace)
                logger.info(f"✓ Deleted vectors matching filter: {filter_dict}")

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
        vector: List[float],
        top_k: int = 10,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query vectors by similarity.

        Args:
            vector: Query vector
            top_k: Number of results to return
            namespace: Namespace to search
            filter_dict: Metadata filter
            include_metadata: Include metadata in results

        Returns:
            List of results with score and metadata
        """
        if not self.index:
            raise RuntimeError("No index selected.")

        try:
            response = self.index.query(
                vector=vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_dict,
                include_metadata=include_metadata,
            )

            results = []
            for match in response.matches:
                result = {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else {},
                }
                if hasattr(match, "values") and match.values:
                    result["vector"] = match.values
                results.append(result)

            logger.info(f"✓ Query returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def query_by_text(
        self,
        text: str,
        embedding_function,
        top_k: int = 10,
        namespace: str = "",
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query by text using an embedding function.

        Args:
            text: Query text
            embedding_function: Function that converts text to vector
            top_k: Number of results
            namespace: Namespace
            filter_dict: Metadata filter

        Returns:
            List of results
        """
        try:
            vector = embedding_function(text)
            return self.query(vector, top_k, namespace, filter_dict)
        except Exception as e:
            logger.error(f"Text query failed: {e}")
            return []

    # ==================== UTILITY METHODS ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.index:
            raise RuntimeError("No index selected.")

        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": getattr(stats, "index_fullness", None),
                "namespaces": stats.namespaces,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def list_namespaces(self) -> List[str]:
        """List all namespaces in the index."""
        stats = self.get_stats()
        return list(stats.get("namespaces", {}).keys())

    def generate_id(self) -> str:
        """Generate a unique ID for vectors."""
        return str(uuid.uuid4())


# ==================== EXAMPLE USAGE ====================


def example_usage():
    """Demonstrate Pinecone CRUD operations."""
    print("=" * 60)
    print("PINECONE VECTOR DATABASE - EXAMPLE USAGE")
    print("=" * 60)

    # Initialize (will fail without API key, but shows the pattern)
    try:
        pinecone = PineconeIntegration()

        # Connect
        if not pinecone.connect():
            print("❌ Failed to connect")
            return

        # Create index
        pinecone.create_index("semantic-memory", dimension=1536)

        # CREATE: Insert sample vectors
        print("\n--- CREATE ---")
        sample_vectors = [
            VectorRecord(
                id="doc-001",
                vector=[0.1] * 1536,  # In real use: actual embeddings
                metadata={
                    "title": "Introduction to AI",
                    "category": "education",
                    "author": "Alice",
                },
            ),
            VectorRecord(
                id="doc-002",
                vector=[0.2] * 1536,
                metadata={
                    "title": "Machine Learning Basics",
                    "category": "education",
                    "author": "Bob",
                },
            ),
            VectorRecord(
                id="doc-003",
                vector=[0.3] * 1536,
                metadata={
                    "title": "Deep Learning Advanced",
                    "category": "education",
                    "author": "Charlie",
                },
            ),
        ]

        result = pinecone.create(sample_vectors)
        print(f"Created: {result['success']} succeeded, {result['failed']} failed")

        # READ: Fetch by ID
        print("\n--- READ (by ID) ---")
        records = pinecone.read(ids=["doc-001", "doc-002"])
        for r in records:
            print(f"  ID: {r.id}, Metadata: {r.metadata}")

        # READ: Query by filter
        print("\n--- READ (by filter) ---")
        filtered = pinecone.read(filter_dict={"category": "education"}, top_k=5)
        print(f"Found {len(filtered)} education records")

        # UPDATE: Modify metadata
        print("\n--- UPDATE ---")
        updated_vector = VectorRecord(
            id="doc-001",
            vector=[0.15] * 1536,  # New embedding
            metadata={
                "title": "Introduction to AI (Revised)",
                "category": "education",
                "author": "Alice",
                "version": 2,
            },
        )
        result = pinecone.update([updated_vector])
        print(f"Updated: {result['success']} records")

        # QUERY: Semantic search
        print("\n--- QUERY (semantic search) ---")
        query_vector = [0.12] * 1536  # Similar to doc-001
        results = pinecone.query(query_vector, top_k=3)
        for r in results:
            print(
                f"  ID: {r['id']}, Score: {r['score']:.4f}, Title: {r['metadata'].get('title')}"
            )

        # DELETE: Remove by ID
        print("\n--- DELETE (by ID) ---")
        deleted = pinecone.delete(ids=["doc-003"])
        print(f"Deleted: {deleted}")

        # STATS
        print("\n--- INDEX STATS ---")
        stats = pinecone.get_stats()
        print(f"Total vectors: {stats.get('total_vector_count')}")
        print(f"Dimension: {stats.get('dimension')}")

        print("\n✓ Example completed successfully!")

    except ValueError as e:
        print(f"\n⚠️  Configuration needed: {e}")
        print("   Set PINECONE_API_KEY environment variable to run this example")


if __name__ == "__main__":
    example_usage()
