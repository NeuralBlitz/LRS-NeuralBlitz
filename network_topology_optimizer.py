"""
network_topology_optimizer.py
Adaptive Network Topology Optimization for D-MLMAS
"""

import hashlib
import time
import random
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class NodeAddress:
    """Network address of a distributed node"""

    node_id: str
    host: str
    port: int
    last_seen: float = field(default_factory=time.time)
    latency_ms: float = float("inf")
    hops: int = 0

    def distance_to(self, other_node_id: str) -> int:
        """Calculate XOR distance (Kademlia-style)"""
        self_hash = int(hashlib.sha256(self.node_id.encode()).hexdigest(), 16)
        other_hash = int(hashlib.sha256(other_node_id.encode()).hexdigest(), 16)
        return self_hash ^ other_hash

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if isinstance(other, NodeAddress):
            return self.node_id == other.node_id
        return False


class KBucket:
    """
    K-Bucket for Kademlia DHT implementation.
    Maintains up to k nodes at each distance level.
    """

    K = 20  # Maximum nodes per bucket

    def __init__(self, min_distance: int, max_distance: int):
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.nodes: List[NodeAddress] = []
        self.replacement_cache: List[NodeAddress] = []
        self.last_updated = time.time()

    def contains(self, node: NodeAddress) -> bool:
        """Check if node is in this bucket"""
        return any(n.node_id == node.node_id for n in self.nodes)

    def add(self, node: NodeAddress) -> bool:
        """Add node to bucket, return True if successful"""
        if self.contains(node):
            # Move to end (most recently seen)
            self.nodes = [n for n in self.nodes if n.node_id != node.node_id]
            self.nodes.append(node)
            self.last_updated = time.time()
            return True

        if len(self.nodes) < self.K:
            self.nodes.append(node)
            self.last_updated = time.time()
            return True
        else:
            # Bucket full, add to replacement cache
            if len(self.replacement_cache) < self.K:
                self.replacement_cache.append(node)
            return False

    def remove(self, node_id: str) -> bool:
        """Remove node from bucket"""
        original_len = len(self.nodes)
        self.nodes = [n for n in self.nodes if n.node_id != node_id]

        # Try to replace from cache
        if len(self.nodes) < original_len and self.replacement_cache:
            self.nodes.append(self.replacement_cache.pop(0))

        return len(self.nodes) < original_len

    def get_closest(self, target_id: str, count: int = 3) -> List[NodeAddress]:
        """Get closest nodes to target"""
        target_hash = int(hashlib.sha256(target_id.encode()).hexdigest(), 16)

        def distance(node: NodeAddress) -> int:
            node_hash = int(hashlib.sha256(node.node_id.encode()).hexdigest(), 16)
            return node_hash ^ target_hash

        return sorted(self.nodes, key=distance)[:count]


class AdaptiveTopologyManager:
    """
    Manages adaptive network topology with Kademlia DHT + latency optimization
    """

    def __init__(self, node_id: str, alpha: int = 3):
        self.node_id = node_id
        self.alpha = alpha  # Parallelism parameter
        self.buckets: List[KBucket] = []
        self.latency_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.routing_table: Dict[str, NodeAddress] = {}
        self.active_paths: Dict[str, List[str]] = {}  # node_id -> path

        # Initialize 160 buckets (for 160-bit SHA256 hashes)
        for i in range(160):
            self.buckets.append(KBucket(2**i, 2 ** (i + 1)))

        self._initialize_buckets()

    def _initialize_buckets(self):
        """Initialize bucket distance ranges"""
        # Already done in __init__
        pass

    def _get_bucket_index(self, node_id: str) -> int:
        """Get bucket index for a node based on XOR distance"""
        distance = self._xor_distance(self.node_id, node_id)
        if distance == 0:
            return -1  # Self

        # Find highest bit set
        bucket_idx = distance.bit_length() - 1
        return min(bucket_idx, 159)  # Cap at 159

    def _xor_distance(self, id1: str, id2: str) -> int:
        """Calculate XOR distance between two node IDs"""
        hash1 = int(hashlib.sha256(id1.encode()).hexdigest(), 16)
        hash2 = int(hashlib.sha256(id2.encode()).hexdigest(), 16)
        return hash1 ^ hash2

    def add_node(self, node: NodeAddress) -> bool:
        """Add node to appropriate k-bucket"""
        if node.node_id == self.node_id:
            return False

        bucket_idx = self._get_bucket_index(node.node_id)
        if bucket_idx < 0:
            return False

        success = self.buckets[bucket_idx].add(node)
        self.routing_table[node.node_id] = node

        # Update latency matrix
        self._update_latency_metrics(node)

        return success

    def remove_node(self, node_id: str) -> bool:
        """Remove node from all buckets"""
        bucket_idx = self._get_bucket_index(node_id)
        if bucket_idx >= 0:
            self.buckets[bucket_idx].remove(node_id)

        if node_id in self.routing_table:
            del self.routing_table[node_id]

        # Clean up latency matrix
        if node_id in self.latency_matrix:
            del self.latency_matrix[node_id]
        for node in self.latency_matrix:
            if node_id in self.latency_matrix[node]:
                del self.latency_matrix[node][node_id]

        return True

    def find_node(self, target_id: str, count: int = 20) -> List[NodeAddress]:
        """
        Find closest nodes to target using Kademlia lookup algorithm.
        Returns up to 'count' closest nodes.
        """
        results = []
        queried = {self.node_id}

        # Start with closest nodes from our buckets
        candidates = self._get_closest_from_buckets(target_id, count * 2)

        while candidates and len(results) < count:
            # Select alpha closest unqueried nodes
            to_query = [n for n in candidates if n.node_id not in queried][: self.alpha]

            if not to_query:
                break

            # Simulate querying these nodes (in real impl, this would be network calls)
            for node in to_query:
                queried.add(node.node_id)
                results.append(node)

                # Add their closer nodes to candidates
                # (In real impl, would receive these from the queried node)
                closer_nodes = self._simulate_find_node_response(node, target_id)
                for closer in closer_nodes:
                    if closer.node_id not in queried and closer.node_id not in [
                        c.node_id for c in candidates
                    ]:
                        candidates.append(closer)

            # Re-sort by distance
            candidates = sorted(
                [c for c in candidates if c.node_id not in queried],
                key=lambda n: n.distance_to(target_id),
            )

        return results[:count]

    def _get_closest_from_buckets(
        self, target_id: str, count: int
    ) -> List[NodeAddress]:
        """Get closest nodes from local buckets"""
        all_nodes = []
        for bucket in self.buckets:
            all_nodes.extend(bucket.nodes)

        return sorted(all_nodes, key=lambda n: n.distance_to(target_id))[:count]

    def _simulate_find_node_response(
        self, node: NodeAddress, target_id: str
    ) -> List[NodeAddress]:
        """Simulate response from querying a node (for demo purposes)"""
        # In real implementation, this would query the actual node
        return []

    def _update_latency_metrics(self, node: NodeAddress):
        """Update latency measurements"""
        # Measure latency to this node
        # In real impl, this would use actual ping measurements
        if node.latency_ms != float("inf"):
            self.latency_matrix[self.node_id][node.node_id] = node.latency_ms

    def calculate_optimal_path(self, target_id: str) -> List[str]:
        """
        Calculate optimal path to target considering:
        1. XOR distance (DHT proximity)
        2. Latency (network performance)
        3. Hop count (path length)
        """
        # Use Dijkstra-like algorithm with weighted edges
        # Weight = α * latency + β * hop_count + γ * distance_penalty

        if target_id == self.node_id:
            return [self.node_id]

        # Get all known nodes
        all_nodes = set(self.routing_table.keys())
        all_nodes.add(self.node_id)
        all_nodes.add(target_id)

        # Initialize distances
        distances = {node: float("inf") for node in all_nodes}
        distances[self.node_id] = 0
        previous = {node: None for node in all_nodes}
        unvisited = all_nodes.copy()

        while unvisited:
            # Find unvisited node with minimum distance
            current = min(unvisited, key=lambda n: distances[n])
            unvisited.remove(current)

            if current == target_id:
                break

            if distances[current] == float("inf"):
                break

            # Get neighbors
            neighbors = self._get_neighbors(current)

            for neighbor in neighbors:
                if neighbor in unvisited:
                    # Calculate edge weight
                    weight = self._calculate_edge_weight(current, neighbor, target_id)
                    new_distance = distances[current] + weight

                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous[neighbor] = current

        # Reconstruct path
        path = []
        current = target_id
        while current is not None:
            path.append(current)
            current = previous[current]

        path.reverse()

        if path[0] != self.node_id:
            return []  # No path found

        self.active_paths[target_id] = path
        return path

    def _get_neighbors(self, node_id: str) -> Set[str]:
        """Get neighboring nodes for a given node"""
        if node_id == self.node_id:
            return set(self.routing_table.keys())

        # In real impl, would query the node's routing table
        # For now, return a subset of our routing table
        return set(list(self.routing_table.keys())[:20])

    def _calculate_edge_weight(
        self, from_node: str, to_node: str, target_id: str
    ) -> float:
        """Calculate edge weight for routing decision"""
        latency = self.latency_matrix.get(from_node, {}).get(
            to_node, 50.0
        )  # Default 50ms

        # Distance penalty using XOR metric
        distance_penalty = self._xor_distance(to_node, target_id) / (2**160)

        # Combined weight (tuneable parameters)
        alpha, beta = 0.7, 0.3
        return alpha * (latency / 100.0) + beta * distance_penalty

    def optimize_topology(self):
        """
        Periodically optimize the network topology:
        1. Refresh stale entries
        2. Rebalance k-buckets
        3. Update latency measurements
        4. Detect and handle partitioned nodes
        """
        current_time = time.time()

        # Remove stale nodes (not seen for > 1 hour)
        stale_threshold = 3600
        for bucket in self.buckets:
            for node in bucket.nodes[:]:
                if current_time - node.last_seen > stale_threshold:
                    bucket.remove(node.node_id)
                    logger.info(f"Removed stale node: {node.node_id}")

        # Trigger latency measurements for active paths
        for target_id in list(self.active_paths.keys()):
            self._measure_path_latency(target_id)

    def _measure_path_latency(self, target_id: str):
        """Measure end-to-end latency to target"""
        # In real impl, would send ping messages
        pass

    def get_topology_stats(self) -> dict:
        """Get statistics about the network topology"""
        total_nodes = len(self.routing_table)
        total_buckets = sum(1 for b in self.buckets if b.nodes)
        avg_latency = self._calculate_average_latency()

        return {
            "node_id": self.node_id,
            "total_known_nodes": total_nodes,
            "active_buckets": total_buckets,
            "average_latency_ms": avg_latency,
            "active_paths": len(self.active_paths),
            "routing_table_size": len(self.routing_table),
        }

    def _calculate_average_latency(self) -> float:
        """Calculate average latency across all known nodes"""
        latencies = []
        for node_latencies in self.latency_matrix.values():
            latencies.extend(node_latencies.values())

        if not latencies:
            return float("inf")

        return sum(latencies) / len(latencies)


# Usage Example
async def demo_topology_optimization():
    """Demonstrate topology optimization"""
    print("\n" + "=" * 80)
    print("🔧 NETWORK TOPOLOGY OPTIMIZER - DEMO")
    print("=" * 80)

    # Create topology managers for multiple nodes
    nodes = []
    for i in range(10):
        node = AdaptiveTopologyManager(f"node_{i}")
        nodes.append(node)

    # Bootstrap: Connect nodes to each other
    print("\n📡 Bootstrapping network topology...")
    for i, node in enumerate(nodes):
        # Connect to 3 random other nodes
        for j in random.sample(range(10), min(3, 10)):
            if i != j:
                addr = NodeAddress(
                    node_id=f"node_{j}",
                    host=f"192.168.1.{100 + j}",
                    port=8000 + j,
                    latency_ms=random.uniform(10, 100),
                )
                node.add_node(addr)

    # Simulate lookup
    print("\n🔍 Testing node lookup...")
    target = "node_5"
    closest = nodes[0].find_node(target, count=5)
    print(f"Closest nodes to {target}:")
    for n in closest:
        dist = n.distance_to(target)
        print(f"  {n.node_id}: distance={dist}, latency={n.latency_ms:.1f}ms")

    # Calculate optimal path
    print("\n🛣️  Calculating optimal path...")
    path = nodes[0].calculate_optimal_path("node_5")
    print(f"Optimal path from node_0 to node_5: {' -> '.join(path)}")

    # Get stats
    print("\n📊 Topology Statistics:")
    stats = nodes[0].get_topology_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return nodes


if __name__ == "__main__":
    asyncio.run(demo_topology_optimization())
