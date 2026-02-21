"""
Weaviate Vector Database Integration
Purpose: Knowledge graph storage with vector search capabilities
Author: NeuralBlitz Research Team
"""

import os
import logging
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import weaviate
try:
    import weaviate
    from weaviate.classes.config import Configure, Property, DataType
    from weaviate.classes.query import Filter

    WEAVIATE_AVAILABLE = True
except ImportError:
    logger.warning("Weaviate client not installed. Run: pip install weaviate-client")
    WEAVIATE_AVAILABLE = False


@dataclass
class KnowledgeNode:
    """Represents a node in the knowledge graph."""

    id: Optional[str] = None
    concept: str = ""
    description: str = ""
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class KnowledgeEdge:
    """Represents a relationship/edge in the knowledge graph."""

    from_id: str
    to_id: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


class WeaviateIntegration:
    """
    Weaviate vector database integration for knowledge graph storage.

    Features:
    - Schema-based knowledge graph modeling
    - CRUD operations on knowledge nodes and edges
    - Hybrid search (BM25 + vector similarity)
    - GraphQL query interface
    - Automatic embedding generation (optional)
    - Batch operations for large datasets
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        embedded: bool = False,
    ):
        """
        Initialize Weaviate integration.

        Args:
            url: Weaviate instance URL
            api_key: API key for authentication (optional)
            embedded: Use embedded mode (local, no server required)
        """
        if not WEAVIATE_AVAILABLE:
            raise ImportError(
                "Weaviate client not installed. Run: pip install weaviate-client"
            )

        self.url = url or os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.embedded = embedded
        self.client = None
        self.schema_defined = False

    def connect(self) -> bool:
        """Initialize connection to Weaviate."""
        try:
            if self.embedded:
                # Use embedded mode (great for development)
                self.client = weaviate.connect_to_embedded()
                logger.info("✓ Connected to Weaviate (embedded mode)")
            elif self.api_key:
                # Cloud/remote instance with auth
                self.client = weaviate.connect_to_wcs(
                    cluster_url=self.url,
                    auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                )
                logger.info(f"✓ Connected to Weaviate Cloud: {self.url}")
            else:
                # Local instance without auth
                self.client = weaviate.connect_to_local()
                logger.info("✓ Connected to Weaviate (local)")

            # Test connection
            if self.client.is_ready():
                meta = self.client.get_meta()
                logger.info(f"  Version: {meta.get('version', 'unknown')}")
                return True
            else:
                logger.error("Weaviate is not ready")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False

    def close(self):
        """Close connection."""
        if self.client:
            self.client.close()
            logger.info("✓ Disconnected from Weaviate")

    # ==================== SCHEMA MANAGEMENT ====================

    def define_knowledge_schema(self, class_name: str = "KnowledgeNode") -> bool:
        """
        Define the schema for knowledge graph storage.

        Args:
            class_name: Name of the class/collection

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Check if class already exists
            if self.client.collections.exists(class_name):
                logger.info(f"Class '{class_name}' already exists")
                return True

            # Define schema with properties
            self.client.collections.create(
                name=class_name,
                vectorizer_config=Configure.Vectorizer.none(),  # We'll provide vectors manually
                properties=[
                    Property(name="concept", data_type=DataType.TEXT),
                    Property(name="description", data_type=DataType.TEXT),
                    Property(name="category", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="confidence", data_type=DataType.NUMBER),
                    Property(name="created_at", data_type=DataType.DATE),
                    Property(name="metadata", data_type=DataType.OBJECT),
                    Property(name="tags", data_type=DataType.TEXT_ARRAY),
                ],
            )

            self.schema_defined = True
            logger.info(f"✓ Created schema: {class_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to define schema: {e}")
            return False

    def create_relation_schema(
        self, class_name: str = "KnowledgeNode", relation_class: str = "KnowledgeEdge"
    ) -> bool:
        """
        Define schema for relationships between knowledge nodes.

        Args:
            class_name: Source node class
            relation_class: Edge/relationship class
        """
        try:
            if self.client.collections.exists(relation_class):
                logger.info(f"Relation class '{relation_class}' already exists")
                return True

            self.client.collections.create(
                name=relation_class,
                properties=[
                    Property(name="relation_type", data_type=DataType.TEXT),
                    Property(name="strength", data_type=DataType.NUMBER),
                    Property(name="bidirectional", data_type=DataType.BOOL),
                    Property(name="properties", data_type=DataType.OBJECT),
                ],
                references=[
                    # Reference to source node
                    {"name": "from_node", "target_collection": class_name},
                    # Reference to target node
                    {"name": "to_node", "target_collection": class_name},
                ],
            )

            logger.info(f"✓ Created relation schema: {relation_class}")
            return True

        except Exception as e:
            logger.error(f"Failed to create relation schema: {e}")
            return False

    # ==================== CRUD OPERATIONS ====================

    def create(
        self,
        nodes: List[KnowledgeNode],
        class_name: str = "KnowledgeNode",
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        CREATE: Insert knowledge nodes into Weaviate.

        Args:
            nodes: List of KnowledgeNode objects
            class_name: Target class/collection
            batch_size: Batch size for insertion

        Returns:
            Dict with operation results
        """
        if not self.client:
            raise RuntimeError("Not connected.")

        results = {"success": 0, "failed": 0, "ids": [], "errors": []}
        collection = self.client.collections.get(class_name)

        try:
            # Use batch import for efficiency
            with collection.batch.dynamic() as batch:
                for node in nodes:
                    try:
                        # Prepare properties
                        properties = {
                            "concept": node.concept,
                            "description": node.description,
                            "created_at": node.created_at,
                            **node.metadata,
                        }

                        # Add to batch
                        if node.vector:
                            batch.add_object(properties=properties, vector=node.vector)
                        else:
                            batch.add_object(properties=properties)

                        results["success"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(
                            {"node": node.concept, "error": str(e)}
                        )

            # Check for batch errors
            if collection.batch.failed_objects:
                for failed in collection.batch.failed_objects:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "object": failed.object_.get("concept"),
                            "error": failed.message,
                        }
                    )

            logger.info(
                f"✓ Created {results['success']} nodes, {results['failed']} failed"
            )
            return results

        except Exception as e:
            logger.error(f"Create operation failed: {e}")
            results["errors"].append(str(e))
            return results

    def read(
        self,
        ids: Optional[List[str]] = None,
        class_name: str = "KnowledgeNode",
        filters: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[KnowledgeNode]:
        """
        READ: Retrieve knowledge nodes by ID or filters.

        Args:
            ids: List of UUIDs to fetch
            class_name: Source class
            filters: Query filters (e.g., {"category": "science"})
            limit: Maximum results

        Returns:
            List of KnowledgeNode objects
        """
        if not self.client:
            raise RuntimeError("Not connected.")

        nodes = []
        collection = self.client.collections.get(class_name)

        try:
            if ids:
                # Fetch by specific IDs
                for obj_id in ids:
                    try:
                        obj = collection.query.fetch_object_by_id(obj_id)
                        if obj:
                            node = self._object_to_node(obj)
                            nodes.append(node)
                    except Exception as e:
                        logger.warning(f"Failed to fetch object {obj_id}: {e}")

            elif filters:
                # Build filter query
                query_filter = self._build_filter(filters)

                response = collection.query.fetch_objects(
                    filters=query_filter, limit=limit
                )

                for obj in response.objects:
                    node = self._object_to_node(obj)
                    nodes.append(node)

            else:
                # Fetch all (up to limit)
                response = collection.query.fetch_objects(limit=limit)
                for obj in response.objects:
                    node = self._object_to_node(obj)
                    nodes.append(node)

            logger.info(f"✓ Retrieved {len(nodes)} nodes")
            return nodes

        except Exception as e:
            logger.error(f"Read operation failed: {e}")
            return []

    def update(
        self, nodes: List[KnowledgeNode], class_name: str = "KnowledgeNode"
    ) -> Dict[str, Any]:
        """
        UPDATE: Modify existing knowledge nodes.

        Args:
            nodes: List of KnowledgeNode objects with IDs
            class_name: Target class

        Returns:
            Dict with operation results
        """
        if not self.client:
            raise RuntimeError("Not connected.")

        results = {"success": 0, "failed": 0, "errors": []}
        collection = self.client.collections.get(class_name)

        try:
            for node in nodes:
                if not node.id:
                    results["failed"] += 1
                    results["errors"].append(
                        {"concept": node.concept, "error": "No ID provided"}
                    )
                    continue

                try:
                    # Update properties
                    properties = {
                        "concept": node.concept,
                        "description": node.description,
                        "updated_at": datetime.utcnow().isoformat(),
                        **node.metadata,
                    }

                    collection.data.update(uuid=node.id, properties=properties)

                    # Update vector if provided
                    if node.vector:
                        collection.data.update(uuid=node.id, vector=node.vector)

                    results["success"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"id": node.id, "error": str(e)})

            logger.info(
                f"✓ Updated {results['success']} nodes, {results['failed']} failed"
            )
            return results

        except Exception as e:
            logger.error(f"Update operation failed: {e}")
            results["errors"].append(str(e))
            return results

    def delete(
        self,
        ids: Optional[List[str]] = None,
        class_name: str = "KnowledgeNode",
        filters: Optional[Dict] = None,
    ) -> bool:
        """
        DELETE: Remove knowledge nodes.

        Args:
            ids: List of UUIDs to delete
            class_name: Target class
            filters: Filter criteria for bulk delete

        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Not connected.")

        collection = self.client.collections.get(class_name)

        try:
            if ids:
                for obj_id in ids:
                    try:
                        collection.data.delete_by_id(obj_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete {obj_id}: {e}")
                logger.info(f"✓ Deleted {len(ids)} nodes by ID")

            elif filters:
                query_filter = self._build_filter(filters)
                collection.data.delete_many(where=query_filter)
                logger.info(f"✓ Deleted nodes matching filter: {filters}")

            else:
                logger.warning("No delete criteria specified")
                return False

            return True

        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return False

    # ==================== KNOWLEDGE GRAPH OPERATIONS ====================

    def create_relationship(
        self,
        edge: KnowledgeEdge,
        class_name: str = "KnowledgeNode",
        relation_class: str = "KnowledgeEdge",
    ) -> bool:
        """
        Create a relationship/edge between two knowledge nodes.

        Args:
            edge: KnowledgeEdge object
            class_name: Node class
            relation_class: Edge class

        Returns:
            True if successful
        """
        try:
            edge_collection = self.client.collections.get(relation_class)

            # Create edge with references
            edge_collection.data.insert(
                {
                    "relation_type": edge.relation_type,
                    "properties": edge.properties,
                    "from_node": weaviate.classes.data.DataReference(
                        from_uuid=edge.from_id, from_property="from_node"
                    ),
                    "to_node": weaviate.classes.data.DataReference(
                        from_uuid=edge.to_id, from_property="to_node"
                    ),
                }
            )

            logger.info(
                f"✓ Created relationship: {edge.from_id} -> {edge.to_id} ({edge.relation_type})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

    def query_graph(
        self,
        start_node_id: str,
        relation_types: Optional[List[str]] = None,
        depth: int = 1,
        class_name: str = "KnowledgeNode",
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph starting from a node.

        Args:
            start_node_id: Starting node UUID
            relation_types: Filter by relation types
            depth: How many hops to traverse
            class_name: Node class

        Returns:
            Graph structure with nodes and edges
        """
        try:
            # This is a simplified graph traversal
            # In production, you'd use Weaviate's GraphQL capabilities

            collection = self.client.collections.get(class_name)
            start_node = collection.query.fetch_object_by_id(start_node_id)

            if not start_node:
                return {"error": "Start node not found"}

            graph = {
                "start_node": self._object_to_node(start_node),
                "nodes": [],
                "edges": [],
                "depth": depth,
            }

            # TODO: Implement actual graph traversal with references
            logger.info(f"✓ Queried graph from node: {start_node_id}")
            return graph

        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": str(e)}

    # ==================== SEMANTIC SEARCH ====================

    def search(
        self,
        query_vector: List[float],
        class_name: str = "KnowledgeNode",
        top_k: int = 10,
        filters: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search.

        Args:
            query_vector: Query embedding
            class_name: Target class
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of results with similarity scores
        """
        if not self.client:
            raise RuntimeError("Not connected.")

        try:
            collection = self.client.collections.get(class_name)

            # Build query
            query_filter = self._build_filter(filters) if filters else None

            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                filters=query_filter,
                return_metadata=["distance"],
            )

            results = []
            for obj in response.objects:
                results.append(
                    {
                        "id": str(obj.uuid),
                        "concept": obj.properties.get("concept"),
                        "description": obj.properties.get("description"),
                        "metadata": {
                            k: v
                            for k, v in obj.properties.items()
                            if k not in ["concept", "description"]
                        },
                        "distance": obj.metadata.distance if obj.metadata else None,
                    }
                )

            logger.info(f"✓ Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        class_name: str = "KnowledgeNode",
        top_k: int = 10,
        alpha: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 text search and vector similarity.

        Args:
            query_text: Text query for BM25
            query_vector: Vector for similarity search
            class_name: Target class
            top_k: Number of results
            alpha: Balance between BM25 (0) and vector (1)

        Returns:
            List of hybrid results
        """
        try:
            collection = self.client.collections.get(class_name)

            response = collection.query.hybrid(
                query=query_text,
                vector=query_vector,
                alpha=alpha,
                limit=top_k,
                return_metadata=["score", "explain_score"],
            )

            results = []
            for obj in response.objects:
                results.append(
                    {
                        "id": str(obj.uuid),
                        "concept": obj.properties.get("concept"),
                        "description": obj.properties.get("description"),
                        "metadata": {
                            k: v
                            for k, v in obj.properties.items()
                            if k not in ["concept", "description"]
                        },
                        "score": obj.metadata.score if obj.metadata else None,
                    }
                )

            logger.info(f"✓ Hybrid search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    # ==================== UTILITY METHODS ====================

    def _object_to_node(self, obj) -> KnowledgeNode:
        """Convert Weaviate object to KnowledgeNode."""
        return KnowledgeNode(
            id=str(obj.uuid),
            concept=obj.properties.get("concept", ""),
            description=obj.properties.get("description", ""),
            vector=obj.vector if hasattr(obj, "vector") else None,
            metadata={
                k: v
                for k, v in obj.properties.items()
                if k not in ["concept", "description", "created_at"]
            },
            created_at=obj.properties.get("created_at"),
        )

    def _build_filter(self, filters: Dict) -> Any:
        """Build Weaviate filter from dict."""
        if not filters:
            return None

        # Simple filter builder - can be extended for complex queries
        conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(Filter.by_property(key).equal(value))
            elif isinstance(value, (int, float)):
                conditions.append(Filter.by_property(key).equal(value))
            elif isinstance(value, list):
                conditions.append(Filter.by_property(key).contains_any(value))

        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            # Combine with AND
            result = conditions[0]
            for cond in conditions[1:]:
                result = result & cond
            return result

        return None

    def get_collection_stats(self, class_name: str = "KnowledgeNode") -> Dict[str, Any]:
        """Get statistics for a collection."""
        try:
            collection = self.client.collections.get(class_name)
            agg = collection.aggregate.over_all()

            return {"total_objects": agg.total_count, "class_name": class_name}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def list_collections(self) -> List[str]:
        """List all collections/classes."""
        try:
            return [c.name for c in self.client.collections.list_all()]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []


# ==================== EXAMPLE USAGE ====================


def example_usage():
    """Demonstrate Weaviate CRUD operations."""
    print("=" * 60)
    print("WEAVIATE KNOWLEDGE GRAPH - EXAMPLE USAGE")
    print("=" * 60)

    try:
        # Initialize with embedded mode (no external server needed)
        weaviate_db = WeaviateIntegration(embedded=True)

        # Connect
        if not weaviate_db.connect():
            print("❌ Failed to connect")
            return

        # Define schema
        print("\n--- SCHEMA DEFINITION ---")
        weaviate_db.define_knowledge_schema("KnowledgeNode")
        weaviate_db.create_relation_schema("KnowledgeNode", "KnowledgeEdge")

        # CREATE: Insert knowledge nodes
        print("\n--- CREATE ---")
        nodes = [
            KnowledgeNode(
                concept="Artificial Intelligence",
                description="The simulation of human intelligence by machines",
                vector=[0.1, 0.2, 0.3] + [0.0] * 381,  # 384-dim vector
                metadata={"category": "technology", "importance": 0.95},
            ),
            KnowledgeNode(
                concept="Machine Learning",
                description="A subset of AI that enables machines to learn from data",
                vector=[0.15, 0.25, 0.35] + [0.0] * 381,
                metadata={"category": "technology", "importance": 0.90},
            ),
            KnowledgeNode(
                concept="Neural Networks",
                description="Computing systems inspired by biological neural networks",
                vector=[0.2, 0.3, 0.4] + [0.0] * 381,
                metadata={"category": "technology", "importance": 0.88},
            ),
        ]

        result = weaviate_db.create(nodes, "KnowledgeNode")
        print(f"Created: {result['success']} succeeded, {result['failed']} failed")

        # READ: Fetch all nodes
        print("\n--- READ ---")
        all_nodes = weaviate_db.read(class_name="KnowledgeNode", limit=10)
        for node in all_nodes:
            print(f"  {node.concept}: {node.description[:50]}...")

        # READ: Query by filter
        print("\n--- READ (filtered) ---")
        filtered = weaviate_db.read(
            filters={"category": "technology"}, class_name="KnowledgeNode"
        )
        print(f"Found {len(filtered)} technology nodes")

        # UPDATE: Modify a node
        if all_nodes:
            print("\n--- UPDATE ---")
            node_to_update = all_nodes[0]
            node_to_update.description = node_to_update.description + " (Updated)"
            result = weaviate_db.update([node_to_update], "KnowledgeNode")
            print(f"Updated: {result['success']} nodes")

        # SEARCH: Vector similarity
        print("\n--- VECTOR SEARCH ---")
        query_vector = [0.12, 0.22, 0.32] + [0.0] * 381  # Similar to AI
        results = weaviate_db.search(query_vector, "KnowledgeNode", top_k=3)
        for r in results:
            print(f"  {r['concept']} (distance: {r['distance']:.4f})")

        # HYBRID SEARCH
        print("\n--- HYBRID SEARCH ---")
        hybrid_results = weaviate_db.hybrid_search(
            query_text="machine intelligence",
            query_vector=[0.12, 0.22, 0.32] + [0.0] * 381,
            class_name="KnowledgeNode",
            top_k=3,
            alpha=0.5,
        )
        for r in hybrid_results:
            print(f"  {r['concept']} (score: {r['score']:.4f})")

        # DELETE
        if all_nodes:
            print("\n--- DELETE ---")
            ids_to_delete = [n.id for n in all_nodes[-1:]]
            deleted = weaviate_db.delete(ids=ids_to_delete, class_name="KnowledgeNode")
            print(f"Deleted: {deleted}")

        # STATS
        print("\n--- COLLECTION STATS ---")
        stats = weaviate_db.get_collection_stats("KnowledgeNode")
        print(f"Total objects: {stats.get('total_objects')}")

        # Cleanup
        weaviate_db.close()

        print("\n✓ Example completed successfully!")

    except ImportError as e:
        print(f"\n⚠️  {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    example_usage()
