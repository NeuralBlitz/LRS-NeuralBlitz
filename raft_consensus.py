"""
raft_consensus.py
Raft-based Distributed Consensus for D-MLMAS
"""

import asyncio
import random
import time
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
import hashlib
import json

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Raft node roles"""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntryType(Enum):
    """Types of log entries"""

    COMMAND = "command"
    CONFIG = "config"
    NO_OP = "no_op"


@dataclass
class LogEntry:
    """Single entry in the Raft log"""

    index: int
    term: int
    entry_type: LogEntryType
    command: Any
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "term": self.term,
            "type": self.entry_type.value,
            "command": self.command,
            "timestamp": self.timestamp,
        }


@dataclass
class RaftState:
    """Persistent Raft state"""

    current_term: int = 0
    voted_for: Optional[str] = None
    log: List[LogEntry] = field(default_factory=list)

    def get_last_log_index(self) -> int:
        return len(self.log) - 1 if self.log else -1

    def get_last_log_term(self) -> int:
        if not self.log:
            return -1
        return self.log[-1].term

    def get_entry(self, index: int) -> Optional[LogEntry]:
        if 0 <= index < len(self.log):
            return self.log[index]
        return None


@dataclass
class VoteRequest:
    """RequestVote RPC arguments"""

    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class VoteResponse:
    """RequestVote RPC results"""

    term: int
    vote_granted: bool
    voter_id: str


@dataclass
class AppendEntriesRequest:
    """AppendEntries RPC arguments"""

    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int


@dataclass
class AppendEntriesResponse:
    """AppendEntries RPC results"""

    term: int
    success: bool
    follower_id: str
    match_index: int = -1


class RaftNode:
    """
    Raft consensus node implementation.

    Implements the Raft consensus algorithm for leader election,
    log replication, and state machine execution.
    """

    # Timing constants (in seconds)
    MIN_ELECTION_TIMEOUT = 0.15  # 150ms
    MAX_ELECTION_TIMEOUT = 0.30  # 300ms
    HEARTBEAT_INTERVAL = 0.05  # 50ms

    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = [p for p in peers if p != node_id]
        self.cluster_size = len(peers) + 1
        self.majority = (self.cluster_size // 2) + 1

        # Raft state
        self.state = RaftState()
        self.role = NodeRole.FOLLOWER

        # Volatile state
        self.commit_index = -1
        self.last_applied = -1

        # Leader state (reinitialized on election)
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # Timing
        self.election_timeout = self._random_timeout()
        self.last_heartbeat = time.time()

        # Channels for async communication
        self.vote_requests: deque = deque()
        self.append_requests: deque = deque()

        # State machine
        self.state_machine: Dict[str, Any] = {}
        self.pending_commands: Dict[str, asyncio.Future] = {}

        # Snapshot
        self.last_snapshot_index = -1
        self.last_snapshot_term = -1

        self._running = False

    def _random_timeout(self) -> float:
        """Generate random election timeout"""
        return random.uniform(self.MIN_ELECTION_TIMEOUT, self.MAX_ELECTION_TIMEOUT)

    async def start(self):
        """Start the Raft node"""
        self._running = True
        logger.info(f"Raft node {self.node_id} starting as {self.role.value}")

        # Start main loop
        asyncio.create_task(self._main_loop())
        asyncio.create_task(self._election_timer())

    async def stop(self):
        """Stop the Raft node"""
        self._running = False
        logger.info(f"Raft node {self.node_id} stopped")

    async def _main_loop(self):
        """Main Raft event loop"""
        while self._running:
            if self.role == NodeRole.LEADER:
                await self._leader_actions()
            elif self.role == NodeRole.CANDIDATE:
                await self._candidate_actions()
            else:  # FOLLOWER
                await self._follower_actions()

            await asyncio.sleep(0.01)  # 10ms tick

    async def _leader_actions(self):
        """Leader periodic actions"""
        current_time = time.time()

        # Send heartbeats
        if current_time - self.last_heartbeat > self.HEARTBEAT_INTERVAL:
            await self._send_heartbeats()
            self.last_heartbeat = current_time

        # Check for commit advancement
        await self._advance_commit_index()

    async def _candidate_actions(self):
        """Candidate periodic actions"""
        # Candidate actions are mostly event-driven
        pass

    async def _follower_actions(self):
        """Follower periodic actions"""
        # Follower actions are mostly event-driven
        pass

    async def _election_timer(self):
        """Election timeout timer"""
        while self._running:
            await asyncio.sleep(0.01)

            if self.role == NodeRole.LEADER:
                continue

            current_time = time.time()
            if current_time - self.last_heartbeat > self.election_timeout:
                await self._start_election()

    async def _start_election(self):
        """Start leader election"""
        self.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.election_timeout = self._random_timeout()
        self.last_heartbeat = time.time()

        logger.info(
            f"Node {self.node_id} starting election for term {self.state.current_term}"
        )

        # Request votes from all peers
        votes_received = 1  # Vote for self
        vote_request = VoteRequest(
            term=self.state.current_term,
            candidate_id=self.node_id,
            last_log_index=self.state.get_last_log_index(),
            last_log_term=self.state.get_last_log_term(),
        )

        # Send vote requests (async)
        vote_tasks = []
        for peer in self.peers:
            task = asyncio.create_task(self._request_vote(peer, vote_request))
            vote_tasks.append(task)

        # Wait for votes with timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*vote_tasks, return_exceptions=True),
                timeout=self.election_timeout,
            )

            for response in responses:
                if isinstance(response, Exception):
                    continue
                if response.vote_granted:
                    votes_received += 1
        except asyncio.TimeoutError:
            pass

        # Check if we won
        if votes_received >= self.majority:
            await self._become_leader()
        else:
            logger.info(
                f"Node {self.node_id} lost election, received {votes_received} votes"
            )

    async def _request_vote(self, peer: str, request: VoteRequest) -> VoteResponse:
        """Request vote from a peer (simulated)"""
        # In real implementation, this would be an RPC call
        # For demo, simulate response
        await asyncio.sleep(random.uniform(0.01, 0.05))

        # Simulate grant/deny (90% grant for demo)
        granted = random.random() < 0.9

        return VoteResponse(term=request.term, vote_granted=granted, voter_id=peer)

    async def _become_leader(self):
        """Transition to leader role"""
        self.role = NodeRole.LEADER
        logger.info(
            f"Node {self.node_id} became leader for term {self.state.current_term}"
        )

        # Initialize leader state
        for peer in self.peers:
            self.next_index[peer] = self.state.get_last_log_index() + 1
            self.match_index[peer] = -1

        # Send immediate heartbeat
        await self._send_heartbeats()
        self.last_heartbeat = time.time()

    async def _send_heartbeats(self):
        """Send heartbeat AppendEntries to all peers"""
        for peer in self.peers:
            asyncio.create_task(self._send_append_entries(peer))

    async def _send_append_entries(
        self, peer: str, entries: Optional[List[LogEntry]] = None
    ):
        """Send AppendEntries RPC to a peer"""
        next_idx = self.next_index.get(peer, 0)
        prev_log_index = next_idx - 1
        prev_log_term = -1

        if prev_log_index >= 0:
            entry = self.state.get_entry(prev_log_index)
            if entry:
                prev_log_term = entry.term

        request = AppendEntriesRequest(
            term=self.state.current_term,
            leader_id=self.node_id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=entries or [],
            leader_commit=self.commit_index,
        )

        # Send RPC (simulated)
        response = await self._send_rpc(peer, request)

        if response.term > self.state.current_term:
            # Step down
            self.state.current_term = response.term
            self.role = NodeRole.FOLLOWER
            self.state.voted_for = None
            return

        if response.success:
            if entries:
                # Update next_index and match_index
                self.match_index[peer] = request.prev_log_index + len(entries)
                self.next_index[peer] = self.match_index[peer] + 1
        else:
            # Decrement next_index and retry
            self.next_index[peer] = max(0, self.next_index[peer] - 1)

    async def _send_rpc(self, peer: str, request: Any) -> Any:
        """Send RPC to peer (simulated)"""
        await asyncio.sleep(random.uniform(0.01, 0.03))

        # Simulate successful response
        if isinstance(request, AppendEntriesRequest):
            return AppendEntriesResponse(
                term=request.term,
                success=True,
                follower_id=peer,
                match_index=request.prev_log_index + len(request.entries),
            )

        return None

    async def _advance_commit_index(self):
        """Advance commit_index based on match_index from followers"""
        for n in range(self.commit_index + 1, self.state.get_last_log_index() + 1):
            # Count replicas
            match_count = 1  # Leader
            for peer in self.peers:
                if self.match_index.get(peer, -1) >= n:
                    match_count += 1

            # Check if majority and from current term
            if match_count >= self.majority:
                entry = self.state.get_entry(n)
                if entry and entry.term == self.state.current_term:
                    self.commit_index = n
                    logger.debug(f"Advanced commit_index to {n}")

                    # Apply to state machine
                    await self._apply_committed_entries()

    async def _apply_committed_entries(self):
        """Apply committed entries to state machine"""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.state.get_entry(self.last_applied)

            if entry:
                await self._apply_entry(entry)

    async def _apply_entry(self, entry: LogEntry):
        """Apply single log entry to state machine"""
        if entry.entry_type == LogEntryType.COMMAND:
            # Apply command
            command_id = entry.command.get("id")
            result = self._execute_command(entry.command)

            # Notify pending command
            if command_id in self.pending_commands:
                future = self.pending_commands.pop(command_id)
                if not future.done():
                    future.set_result(result)

            logger.debug(f"Applied command at index {entry.index}")

    def _execute_command(self, command: Any) -> Any:
        """Execute a state machine command"""
        op = command.get("op")
        key = command.get("key")
        value = command.get("value")

        if op == "set":
            self.state_machine[key] = value
            return {"status": "ok", "value": value}
        elif op == "get":
            return {"status": "ok", "value": self.state_machine.get(key)}
        elif op == "delete":
            if key in self.state_machine:
                del self.state_machine[key]
            return {"status": "ok"}

        return {"status": "error", "message": "unknown operation"}

    async def propose_command(self, command: Any, timeout: float = 5.0) -> Any:
        """
        Propose a command to be replicated.
        Only succeeds if this node is the leader.
        """
        if self.role != NodeRole.LEADER:
            return {"status": "error", "message": "not leader"}

        # Create log entry
        command_id = hashlib.sha256(
            json.dumps(command, sort_keys=True).encode()
        ).hexdigest()[:16]

        command["id"] = command_id

        entry = LogEntry(
            index=len(self.state.log),
            term=self.state.current_term,
            entry_type=LogEntryType.COMMAND,
            command=command,
        )

        # Append to local log
        self.state.log.append(entry)

        # Create future for result
        future = asyncio.Future()
        self.pending_commands[command_id] = future

        # Replicate to followers
        for peer in self.peers:
            asyncio.create_task(self._send_append_entries(peer, [entry]))

        # Wait for commit with timeout
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.pending_commands.pop(command_id, None)
            return {"status": "error", "message": "timeout waiting for commit"}

    def get_status(self) -> dict:
        """Get node status"""
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "term": self.state.current_term,
            "log_size": len(self.state.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "state_machine_size": len(self.state_machine),
            "leader": self.role == NodeRole.LEADER,
        }


class RaftCluster:
    """Manages a cluster of Raft nodes"""

    def __init__(self, node_ids: List[str]):
        self.node_ids = node_ids
        self.nodes: Dict[str, RaftNode] = {}

    async def start(self):
        """Start all nodes in the cluster"""
        for node_id in self.node_ids:
            node = RaftNode(node_id, self.node_ids)
            self.nodes[node_id] = node
            await node.start()

        logger.info(f"Raft cluster started with {len(self.nodes)} nodes")

    async def stop(self):
        """Stop all nodes"""
        for node in self.nodes.values():
            await node.stop()

    def get_leader(self) -> Optional[RaftNode]:
        """Get current leader"""
        for node in self.nodes.values():
            if node.role == NodeRole.LEADER:
                return node
        return None

    async def submit_command(self, command: Any) -> Any:
        """Submit command to leader"""
        leader = self.get_leader()
        if leader:
            return await leader.propose_command(command)
        return {"status": "error", "message": "no leader"}


# Usage Example
async def demo_raft_consensus():
    """Demonstrate Raft consensus"""
    print("\n" + "=" * 80)
    print("⚖️  RAFT CONSENSUS LAYER - DEMO")
    print("=" * 80)

    # Create cluster
    node_ids = ["node_0", "node_1", "node_2", "node_3", "node_4"]
    cluster = RaftCluster(node_ids)

    # Start cluster
    print("\n🚀 Starting Raft cluster...")
    await cluster.start()
    await asyncio.sleep(0.5)  # Wait for leader election

    # Check leader
    leader = cluster.get_leader()
    if leader:
        print(f"  ✓ Leader elected: {leader.node_id}")
    else:
        print("  ⚠ No leader yet, waiting...")
        await asyncio.sleep(1.0)
        leader = cluster.get_leader()

    # Submit commands
    print("\n📤 Submitting commands to cluster...")
    commands = [
        {"op": "set", "key": "config", "value": {"nodes": 5}},
        {"op": "set", "key": "task_queue", "value": ["task_1", "task_2"]},
        {"op": "set", "key": "status", "value": "active"},
    ]

    for i, cmd in enumerate(commands):
        result = await cluster.submit_command(cmd)
        status = "✓" if result.get("status") == "ok" else "✗"
        print(f"  {status} Command {i + 1}: {cmd['op']} {cmd['key']}")
        await asyncio.sleep(0.1)

    # Check replication
    print("\n📊 Checking state replication...")
    await asyncio.sleep(0.3)

    for node_id, node in cluster.nodes.items():
        status = node.get_status()
        print(f"  {node_id}:")
        print(f"    Role: {status['role']}")
        print(f"    Log size: {status['log_size']}")
        print(f"    Commit index: {status['commit_index']}")
        print(f"    State machine keys: {status['state_machine_size']}")

    # Stop cluster
    print("\n🛑 Stopping cluster...")
    await cluster.stop()

    return cluster


if __name__ == "__main__":
    asyncio.run(demo_raft_consensus())
