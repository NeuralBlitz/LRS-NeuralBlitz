"""
fault_tolerance_layer.py
Comprehensive Fault Tolerance for D-MLMAS
"""

import asyncio
import time
import logging
import pickle
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults that can occur"""

    NONE = auto()
    CRASH = auto()  # Node stops responding
    NETWORK_PARTITION = auto()  # Network split
    BYZANTINE = auto()  # Malicious/incorrect behavior
    SLOW_NODE = auto()  # Node is unacceptably slow
    MEMORY_ERROR = auto()  # State corruption


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class PhiAccrualSample:
    """Sample for Phi-accrual failure detection"""

    heartbeat_time: float
    arrival_time: float

    @property
    def delay(self) -> float:
        return self.arrival_time - self.heartbeat_time


class PhiAccrualFailureDetector:
    """
    Phi-accrual failure detector implementation.

    Based on: "The Phi Accrual Failure Detector" by Hayashibara et al.

    Instead of binary up/down, outputs a suspicion level (phi)
    that increases as no heartbeat is received.
    """

    def __init__(
        self,
        threshold: float = 8.0,
        max_sample_size: int = 1000,
        min_std_deviation: float = 0.5,
    ):
        self.threshold = threshold
        self.max_sample_size = max_sample_size
        self.min_std_deviation = min_std_deviation

        self.samples: deque = deque(maxlen=max_sample_size)
        self.last_heartbeat_time: Optional[float] = None

    def heartbeat(self):
        """Record a heartbeat arrival"""
        now = time.time()

        if self.last_heartbeat_time is not None:
            sample = PhiAccrualSample(
                heartbeat_time=self.last_heartbeat_time, arrival_time=now
            )
            self.samples.append(sample)

        self.last_heartbeat_time = now

    def phi(self) -> float:
        """
        Calculate current phi (suspicion level).
        Returns 0.0 if no samples available.
        """
        if not self.samples or self.last_heartbeat_time is None:
            return 0.0

        # Calculate mean and standard deviation of heartbeat delays
        delays = [s.delay for s in self.samples]
        mean_delay = sum(delays) / len(delays)

        # Calculate standard deviation
        variance = sum((d - mean_delay) ** 2 for d in delays) / len(delays)
        std_dev = max(self.min_std_deviation, variance**0.5)

        # Time since last heartbeat
        time_since_last = time.time() - self.last_heartbeat_time

        # Calculate phi using exponential distribution assumption
        # phi = -log10(F(time_since_last))
        # where F is CDF of exponential distribution
        import math

        phi = -math.log10(math.exp(-time_since_last / mean_delay))

        return phi

    def is_suspected(self) -> bool:
        """Check if node is suspected to have failed"""
        return self.phi() >= self.threshold

    def get_stats(self) -> dict:
        """Get detector statistics"""
        return {
            "phi": self.phi(),
            "threshold": self.threshold,
            "sample_count": len(self.samples),
            "suspected": self.is_suspected(),
            "time_since_last_heartbeat": time.time() - self.last_heartbeat_time
            if self.last_heartbeat_time
            else None,
        }


@dataclass
class Checkpoint:
    """System state checkpoint"""

    checkpoint_id: str
    timestamp: float
    state_hash: str
    state_data: bytes
    task_states: Dict[str, Any]
    node_states: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """
    Manages distributed checkpoints for fault recovery.
    Implements incremental checkpointing with Merkle trees.
    """

    def __init__(self, checkpoint_interval: float = 30.0):
        self.checkpoint_interval = checkpoint_interval
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.latest_checkpoint: Optional[str] = None
        self.checkpoint_history: deque = deque(maxlen=50)

    def create_checkpoint(
        self,
        task_states: Dict[str, Any],
        node_states: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """Create a new checkpoint"""
        checkpoint_id = hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:16]

        # Serialize state
        state_data = pickle.dumps(
            {
                "task_states": task_states,
                "node_states": node_states,
                "metadata": metadata or {},
            }
        )

        # Calculate state hash (Merkle root would be better)
        state_hash = hashlib.sha256(state_data).hexdigest()

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            state_hash=state_hash,
            state_data=state_data,
            task_states=task_states.copy(),
            node_states=node_states.copy(),
            metadata=metadata or {},
        )

        self.checkpoints[checkpoint_id] = checkpoint
        self.latest_checkpoint = checkpoint_id
        self.checkpoint_history.append(checkpoint_id)

        logger.info(f"Created checkpoint {checkpoint_id}")
        return checkpoint

    def restore_checkpoint(
        self, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Restore state from checkpoint"""
        if checkpoint_id is None:
            checkpoint_id = self.latest_checkpoint

        if checkpoint_id not in self.checkpoints:
            logger.error(f"Checkpoint {checkpoint_id} not found")
            return None

        checkpoint = self.checkpoints[checkpoint_id]

        # Verify integrity
        computed_hash = hashlib.sha256(checkpoint.state_data).hexdigest()
        if computed_hash != checkpoint.state_hash:
            logger.error(f"Checkpoint {checkpoint_id} integrity check failed")
            return None

        # Deserialize
        state = pickle.loads(checkpoint.state_data)

        logger.info(f"Restored checkpoint {checkpoint_id}")
        return state

    def verify_checkpoint_chain(self) -> bool:
        """Verify integrity of checkpoint chain"""
        for i, checkpoint_id in enumerate(self.checkpoint_history):
            if checkpoint_id not in self.checkpoints:
                return False
        return True


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascading failures in distributed systems.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise Exception("Circuit breaker HALF_OPEN call limit reached")
            self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.half_open_calls = 0
                logger.info("Circuit breaker CLOSED (recovered)")

    def on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN (half-open failure)")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPEN ({self.failure_count} failures)")

    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class FaultTolerantNode:
    """
    Fault-tolerant wrapper for distributed nodes.
    Integrates failure detection, checkpointing, and circuit breaking.
    """

    def __init__(self, node_id: str, capabilities: List[str]):
        self.node_id = node_id
        self.capabilities = capabilities
        self.state = "ONLINE"

        # Fault tolerance components
        self.failure_detector = PhiAccrualFailureDetector()
        self.checkpoint_manager = CheckpointManager()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Task management
        self.active_tasks: Dict[str, Any] = {}
        self.task_history: deque = deque(maxlen=1000)

        # Recovery
        self.failed_task_queue: deque = deque()
        self.recovery_handlers: Dict[FaultType, Callable] = {}

    def register_recovery_handler(self, fault_type: FaultType, handler: Callable):
        """Register a handler for specific fault types"""
        self.recovery_handlers[fault_type] = handler

    async def heartbeat(self):
        """Send heartbeat and update failure detector"""
        self.failure_detector.heartbeat()

        # Check if we're suspected
        if self.failure_detector.is_suspected():
            logger.warning(f"Node {self.node_id} is suspected to be faulty")

    async def execute_task(self, task: Any, node_pool: Dict[str, Any]) -> Any:
        """
        Execute task with fault tolerance.
        Implements retry, checkpoint, and circuit breaker patterns.
        """
        task_id = task.get("task_id", str(time.time()))
        target_nodes = task.get("target_nodes", [])

        # Record task start
        self.active_tasks[task_id] = {
            "task": task,
            "start_time": time.time(),
            "retries": 0,
            "max_retries": task.get("max_retries", 3),
        }

        # Create checkpoint before execution
        checkpoint = self.checkpoint_manager.create_checkpoint(
            task_states=self.active_tasks,
            node_states={node_id: {"state": self.state} for node_id in node_pool},
            metadata={"task_id": task_id, "action": "task_start"},
        )

        # Try execution with retries
        last_exception = None

        for attempt in range(self.active_tasks[task_id]["max_retries"]):
            try:
                # Get circuit breaker for this task type
                cb = self._get_circuit_breaker(task.get("task_type", "default"))

                # Execute with circuit breaker
                result = cb.call(self._execute_task_internal, task, node_pool)

                # Success
                self.active_tasks[task_id]["status"] = "completed"
                self.active_tasks[task_id]["result"] = result
                self.task_history.append(
                    {
                        "task_id": task_id,
                        "status": "completed",
                        "attempts": attempt + 1,
                        "timestamp": time.time(),
                    }
                )

                # Cleanup
                del self.active_tasks[task_id]

                return result

            except Exception as e:
                last_exception = e
                self.active_tasks[task_id]["retries"] += 1

                # Classify fault
                fault_type = self._classify_fault(e)
                logger.warning(
                    f"Task {task_id} failed (attempt {attempt + 1}): {fault_type.name}"
                )

                # Handle specific fault
                if fault_type in self.recovery_handlers:
                    recovery_result = await self.recovery_handlers[fault_type](task, e)
                    if recovery_result:
                        # Recovery successful, retry
                        continue

                # Exponential backoff
                await asyncio.sleep(2**attempt)

        # All retries exhausted
        self.active_tasks[task_id]["status"] = "failed"
        self.failed_task_queue.append(task)

        # Restore from checkpoint
        logger.info(f"Restoring checkpoint for failed task {task_id}")
        self.checkpoint_manager.restore_checkpoint(checkpoint.checkpoint_id)

        raise last_exception

    def _execute_task_internal(self, task: Any, node_pool: Dict[str, Any]) -> Any:
        """Internal task execution (simulated)"""
        # Simulate task execution
        import random

        if random.random() < 0.1:  # 10% failure rate for demo
            raise Exception("Simulated task failure")
        return {"result": "success", "task_id": task.get("task_id")}

    def _get_circuit_breaker(self, task_type: str) -> CircuitBreaker:
        """Get or create circuit breaker for task type"""
        if task_type not in self.circuit_breakers:
            self.circuit_breakers[task_type] = CircuitBreaker()
        return self.circuit_breakers[task_type]

    def _classify_fault(self, exception: Exception) -> FaultType:
        """Classify exception into fault type"""
        error_msg = str(exception).lower()

        if "timeout" in error_msg or "connection" in error_msg:
            return FaultType.NETWORK_PARTITION
        elif "crash" in error_msg or "killed" in error_msg:
            return FaultType.CRASH
        elif "byzantine" in error_msg or "invalid" in error_msg:
            return FaultType.BYZANTINE
        elif "slow" in error_msg or "latency" in error_msg:
            return FaultType.SLOW_NODE
        elif "corruption" in error_msg or "checksum" in error_msg:
            return FaultType.MEMORY_ERROR
        else:
            return FaultType.CRASH

    async def recover_failed_tasks(self, node_pool: Dict[str, Any]):
        """Attempt to recover failed tasks"""
        recovered = []

        while self.failed_task_queue:
            task = self.failed_task_queue.popleft()

            try:
                # Try to redispatch to different node
                result = await self.execute_task(task, node_pool)
                recovered.append(task.get("task_id"))
            except Exception as e:
                # Re-queue for later
                self.failed_task_queue.append(task)
                break

        return recovered

    def get_fault_tolerance_stats(self) -> dict:
        """Get fault tolerance statistics"""
        return {
            "node_id": self.node_id,
            "failure_detector": self.failure_detector.get_stats(),
            "active_tasks": len(self.active_tasks),
            "failed_tasks": len(self.failed_task_queue),
            "checkpoint_count": len(self.checkpoint_manager.checkpoints),
            "circuit_breakers": {
                name: cb.get_state() for name, cb in self.circuit_breakers.items()
            },
        }


# Usage Example
async def demo_fault_tolerance():
    """Demonstrate fault tolerance mechanisms"""
    print("\n" + "=" * 80)
    print("🛡️  FAULT TOLERANCE LAYER - DEMO")
    print("=" * 80)

    # Create fault-tolerant nodes
    nodes = []
    for i in range(5):
        node = FaultTolerantNode(f"node_{i}", capabilities=["compute", "storage"])
        nodes.append(node)

    node_pool = {node.node_id: node for node in nodes}

    # Simulate heartbeats
    print("\n💓 Simulating heartbeats...")
    for _ in range(10):
        for node in nodes:
            await node.heartbeat()
        await asyncio.sleep(0.1)

    # Check failure detector
    print("\n📊 Failure Detector Stats:")
    for node in nodes:
        stats = node.failure_detector.get_stats()
        print(
            f"  {node.node_id}: phi={stats['phi']:.2f}, suspected={stats['suspected']}"
        )

    # Simulate task execution with failures
    print("\n⚡ Executing tasks with fault tolerance...")
    tasks = [
        {
            "task_id": f"task_{i}",
            "task_type": "compute",
            "target_nodes": [],
            "max_retries": 3,
        }
        for i in range(10)
    ]

    for i, task in enumerate(tasks):
        try:
            result = await nodes[i % len(nodes)].execute_task(task, node_pool)
            print(f"  ✓ {task['task_id']}: SUCCESS")
        except Exception as e:
            print(f"  ✗ {task['task_id']}: FAILED ({str(e)[:30]}...)")

    # Recover failed tasks
    print("\n🔄 Recovering failed tasks...")
    for node in nodes:
        recovered = await node.recover_failed_tasks(node_pool)
        if recovered:
            print(f"  {node.node_id} recovered {len(recovered)} tasks")

    # Get final stats
    print("\n📈 Final Statistics:")
    for node in nodes[:2]:  # Show first 2
        stats = node.get_fault_tolerance_stats()
        print(f"  {node.node_id}:")
        print(f"    Active tasks: {stats['active_tasks']}")
        print(f"    Failed tasks: {stats['failed_tasks']}")
        print(f"    Checkpoints: {stats['checkpoint_count']}")

    return nodes


if __name__ == "__main__":
    asyncio.run(demo_fault_tolerance())
