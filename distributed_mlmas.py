"""
Distributed Multi-Layered Multi-Agent System (D-MLMAS)
=====================================================

Extended MLMAS with distributed computing capabilities:
- Multi-node coordination
- Cross-cluster communication
- Load balancing across nodes
- Fault tolerance and recovery
- Network-aware task distribution

Based on NeuralBlitz v20.0 architecture
"""

import asyncio
import json
import uuid
import time
import hashlib
import logging
import socket
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import random
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("D-MLMAS")


class NodeState(Enum):
    """States for distributed nodes"""

    OFFLINE = "offline"
    ONLINE = "online"
    ACTIVE = "active"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


class TaskStatus(Enum):
    """Status of distributed tasks"""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeConfig:
    """Configuration for a distributed node"""

    node_id: str
    hostname: str
    port: int
    capabilities: List[str]
    max_agents: int
    max_tasks: int
    cpu_cores: int = 4
    memory_gb: int = 16
    priority: int = 1


@dataclass
class DistributedTask:
    """Task to be distributed across nodes"""

    task_id: str
    name: str
    payload: Dict[str, Any]
    required_capabilities: List[str]
    priority: int
    timeout: float = 60.0
    retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    target_node: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NodeMetrics:
    """Metrics for a node"""

    node_id: str
    cpu_usage: float
    memory_usage: float
    active_agents: int
    active_tasks: int
    queue_length: int
    tasks_completed: int
    tasks_failed: int
    last_heartbeat: datetime


class Node:
    """Represents a node in the distributed system"""

    def __init__(self, config: NodeConfig):
        self.config = config
        self.state = NodeState.OFFLINE
        self.metrics = None
        self.task_queue = deque()
        self.active_tasks: Dict[str, DistributedTask] = {}
        self.completed_tasks = []
        self.failed_tasks = []
        self.start_time = None

    async def start(self):
        """Start the node"""
        self.state = NodeState.ONLINE
        self.start_time = datetime.now()
        logger.info(
            f"Node {self.config.node_id} started on {self.config.hostname}:{self.config.port}"
        )

    async def stop(self):
        """Stop the node"""
        self.state = NodeState.OFFLINE
        logger.info(f"Node {self.config.node_id} stopped")

    async def heartbeat(self) -> NodeMetrics:
        """Generate heartbeat with metrics"""
        self.metrics = NodeMetrics(
            node_id=self.config.node_id,
            cpu_usage=random.uniform(0.1, 0.8),
            memory_usage=random.uniform(0.2, 0.7),
            active_agents=random.randint(0, self.config.max_agents),
            active_tasks=len(self.active_tasks),
            queue_length=len(self.task_queue),
            tasks_completed=random.randint(100, 10000),
            tasks_failed=random.randint(0, 50),
            last_heartbeat=datetime.now(),
        )
        return self.metrics

    def can_accept_task(self, task: DistributedTask) -> bool:
        """Check if node can accept a task"""
        if self.state != NodeState.ONLINE and self.state != NodeState.ACTIVE:
            return False
        if len(self.active_tasks) >= self.config.max_tasks:
            return False
        if not all(
            cap in self.config.capabilities for cap in task.required_capabilities
        ):
            return False
        return True


class DistributedScheduler:
    """Scheduler for distributing tasks across nodes"""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.pending_tasks: deque = deque()
        self.completed_tasks: List[DistributedTask] = []
        self.failed_tasks: List[DistributedTask] = []
        self.task_results: Dict[str, Any] = {}
        self调度_id = str(uuid.uuid4())
        self.start_time = None

    def register_node(self, node: Node):
        """Register a node with the scheduler"""
        self.nodes[node.config.node_id] = node
        logger.info(f"Registered node: {node.config.node_id}")

    def deregister_node(self, node_id: str):
        """Deregister a node"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"Deregistered node: {node_id}")

    def submit_task(self, task: DistributedTask):
        """Submit a task for distribution"""
        self.pending_tasks.append(task)
        logger.info(f"Submitted task: {task.task_id}")

    def submit_tasks(self, tasks: List[DistributedTask]):
        """Submit multiple tasks"""
        for task in tasks:
            self.submit_task(task)

    def find_best_node(self, task: DistributedTask) -> Optional[str]:
        """Find the best node for a task"""
        eligible = [
            nid for nid, node in self.nodes.items() if node.can_accept_task(task)
        ]

        if not eligible:
            return None

        # Score nodes based on metrics
        scores = {}
        for nid in eligible:
            node = self.nodes[nid]

            # Ensure metrics exist
            if node.metrics is None:
                # Create default metrics if heartbeat hasn't run
                metrics = NodeMetrics(
                    node_id=node.config.node_id,
                    cpu_usage=0.5,
                    memory_usage=0.5,
                    active_agents=5,
                    active_tasks=len(node.active_tasks),
                    queue_length=len(node.task_queue),
                    tasks_completed=100,
                    tasks_failed=5,
                    last_heartbeat=datetime.now(),
                )
            else:
                metrics = node.metrics

            # Lower is better for these metrics
            load_score = (
                metrics.cpu_usage * 0.3
                + metrics.memory_usage * 0.3
                + (metrics.active_tasks / max(1, node.config.max_tasks)) * 0.2
                + (metrics.queue_length / 100) * 0.2
            )

            # Higher priority nodes score better
            priority_score = node.config.priority / max(
                n.config.priority for n in self.nodes.values()
            )

            scores[nid] = float(load_score - priority_score * 0.1)

        # Return best node (lowest score)
        if scores:
            return min(scores.keys(), key=lambda k: scores[k])
        return None

    async def dispatch_tasks(self) -> Dict[str, int]:
        """Dispatch pending tasks to nodes"""
        dispatched = {"success": 0, "failed": 0}

        while self.pending_tasks:
            task = self.pending_tasks[0]

            # Check dependencies
            deps_completed = all(
                self.task_results.get(dep, {}).get("status") == "completed"
                for dep in task.dependencies
            )

            if not deps_completed:
                await asyncio.sleep(0.1)
                continue

            # Find best node
            node_id = self.find_best_node(task)

            if node_id:
                node = self.nodes[node_id]
                if node.can_accept_task(task):
                    # Assign task
                    task.status = TaskStatus.DISPATCHED
                    task.target_node = node_id
                    node.task_queue.append(task)
                    node.active_tasks[task.task_id] = task
                    self.pending_tasks.popleft()

                    # Simulate async execution
                    asyncio.create_task(self._execute_task(node, task))

                    dispatched["success"] += 1
                    logger.info(f"Dispatched task {task.task_id} to node {node_id}")
                else:
                    dispatched["failed"] += 1
            else:
                # No eligible node, retry later
                await asyncio.sleep(0.1)

        return dispatched

    async def _execute_task(self, node: Node, task: DistributedTask):
        """Execute a task on a node (simulated)"""
        try:
            # Simulate processing
            await asyncio.sleep(random.uniform(0.1, 0.5))

            # Random success/failure (90% success rate)
            if random.random() < 0.9:
                task.status = TaskStatus.COMPLETED
                self.task_results[task.task_id] = {
                    "status": "completed",
                    "result": f"Result from {node.config.node_id}",
                    "node_id": node.config.node_id,
                    "execution_time": random.uniform(0.1, 0.5),
                }
                node.completed_tasks.append(task)
            else:
                raise Exception("Simulated task failure")

        except Exception as e:
            task.status = TaskStatus.FAILED
            self.task_results[task.task_id] = {
                "status": "failed",
                "error": str(e),
                "node_id": node.config.node_id,
            }
            node.failed_tasks.append(task)

            # Retry logic
            if task.retries > 0:
                task.retries -= 1
                task.status = TaskStatus.PENDING
                self.pending_tasks.appendleft(task)

        finally:
            if task.task_id in node.active_tasks:
                del node.active_tasks[task.task_id]

    async def recover_failed_tasks(self):
        """Recover tasks from failed nodes"""
        for task_id, result in list(self.task_results.items()):
            if result["status"] == "failed":
                # Find original task and resubmit
                original = DistributedTask(
                    task_id=task_id,
                    name="recovered_task",
                    payload={},
                    required_capabilities=[],
                    priority=1,
                )
                self.submit_task(original)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        total_nodes = len(self.nodes)
        active_nodes = sum(
            1 for n in self.nodes.values() if n.state == NodeState.ACTIVE
        )
        online_nodes = sum(
            1
            for n in self.nodes.values()
            if n.state in [NodeState.ACTIVE, NodeState.ONLINE]
        )

        return {
            "调度_id": self.调度_id,
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "online_nodes": online_nodes,
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "total_tasks": len(self.task_results),
        }


class DistributedMLMAS:
    """Main distributed MLMAS orchestrator"""

    def __init__(self, num_nodes: int = 4, tasks_per_stage: int = 500):
        self.num_nodes = num_nodes
        self.tasks_per_stage = tasks_per_stage
        self.scheduler = DistributedScheduler()
        self.stages_completed = 0
        self.total_tasks_processed = 0
        self.start_time = None

    async def initialize_nodes(self):
        """Initialize distributed nodes"""
        logger.info(f"Initializing {self.num_nodes} nodes...")

        for i in range(self.num_nodes):
            config = NodeConfig(
                node_id=f"node_{i}",
                hostname=f"192.168.1.{100 + i}",
                port=8000 + i,
                capabilities=[f"cap_{j}" for j in range(5)],
                max_agents=10,
                max_tasks=100,
                cpu_cores=8,
                memory_gb=32,
                priority=i + 1,
            )

            node = Node(config)
            await node.start()
            self.scheduler.register_node(node)

        logger.info(f"Initialized {self.num_nodes} nodes")

    def generate_tasks(self, stage: int) -> List[DistributedTask]:
        """Generate tasks for a stage"""
        tasks = []

        for i in range(self.tasks_per_stage):
            task = DistributedTask(
                task_id=f"stage{stage}_task{i}_{uuid.uuid4().hex[:8]}",
                name=f"Task {i} Stage {stage}",
                payload={"stage": stage, "index": i},
                required_capabilities=[f"cap_{random.randint(0, 4)}"],
                priority=random.randint(1, 5),
                timeout=60.0,
                retries=3,
            )
            tasks.append(task)

        return tasks

    async def run_stages(self, num_stages: int = 50) -> Dict[str, Any]:
        """Run multiple stages of distributed processing"""
        self.start_time = datetime.now()
        stage_results = []

        logger.info(
            f"Starting D-MLMAS with {num_stages} stages, {self.tasks_per_stage} tasks/stage"
        )

        for stage in range(num_stages):
            self.stages_completed = stage

            # Generate tasks for this stage
            tasks = self.generate_tasks(stage)

            # Submit tasks
            self.scheduler.submit_tasks(tasks)

            # Dispatch tasks
            dispatch_result = await self.scheduler.dispatch_tasks()

            # Wait for completion
            await asyncio.sleep(0.5)

            # Record stage result
            stage_result = {
                "stage": stage,
                "tasks_generated": len(tasks),
                "dispatched": dispatch_result["success"],
                "failed_initial": dispatch_result["failed"],
                "pending_after": len(self.scheduler.pending_tasks),
                "completed_total": len(self.scheduler.completed_tasks),
                "failed_total": len(self.scheduler.failed_tasks),
            }
            stage_results.append(stage_result)

            if stage % 10 == 0:
                status = self.scheduler.get_scheduler_status()
                logger.info(
                    f"Stage {stage}: {status['completed_tasks']} completed, {status['pending_tasks']} pending"
                )

        total_time = (datetime.now() - self.start_time).total_seconds()

        return {
            "total_stages": num_stages,
            "total_tasks": self.tasks_per_stage * num_stages,
            "total_time": total_time,
            "throughput": (self.tasks_per_stage * num_stages) / total_time
            if total_time > 0
            else 0,
            "stages_completed": self.stages_completed + 1,
            "stage_results": stage_results[-10:],
            "scheduler_status": self.scheduler.get_scheduler_status(),
        }


async def demonstrate_distributed_mlmas():
    """Demonstrate distributed MLMAS"""
    print("\n" + "=" * 80)
    print("🌐 DISTRIBUTED MULTI-LAYERED MULTI-AGENT SYSTEM (D-MLMAS)")
    print("=" * 80)

    # Initialize distributed system
    dm = DistributedMLMAS(num_nodes=4, tasks_per_stage=200)
    await dm.initialize_nodes()

    # Run stages
    results = await dm.run_stages(num_stages=25)

    print("\n" + "=" * 80)
    print("📊 DISTRIBUTED MLMAS RESULTS")
    print("=" * 80)
    print(f"Total Stages: {results['total_stages']}")
    print(f"Total Tasks: {results['total_tasks']}")
    print(f"Total Time: {results['total_time']:.2f} seconds")
    print(f"Throughput: {results['throughput']:.2f} tasks/second")
    print(f"Nodes Active: {results['scheduler_status']['active_nodes']}")
    print("=" * 80)

    return results


if __name__ == "__main__":
    asyncio.run(demonstrate_distributed_mlmas())
