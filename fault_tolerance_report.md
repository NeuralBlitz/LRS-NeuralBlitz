# Fault Tolerance Mechanisms: Comprehensive Design Report

## Executive Summary

This report presents three distinct fault tolerance mechanisms designed for distributed systems, each addressing different failure modes and threat models. The designs include detailed fault models, architectural specifications, and reference implementations.

---

## 1. Checkpoint and Restart Mechanism

### 1.1 Fault Model

**Failure Types Addressed:**
- **Fail-stop failures**: Processes that abruptly terminate (crash, OOM kill, hardware failure)
- **Transient failures**: Temporary network partitions, power fluctuations, resource exhaustion
- **Software bugs**: Non-deterministic crashes, memory corruption, infinite loops (with timeout)

**Assumptions:**
- Failures are detectable (crash-stop semantics)
- Stable storage survives failures
- Checkpoints are consistent (no split-brain during capture)
- Deterministic execution or replayable non-determinism

**Failure Detection:**
- Heartbeat timeouts (heartbeat interval: 1s, timeout: 3s)
- Process watchdog monitoring
- Application-specific health checks

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Worker 1 │  │ Worker 2 │  │ Worker N │                   │
│  │(Primary) │  │(Primary) │  │(Primary) │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       │             │             │                         │
│  ┌────┴─────────────┴─────────────┴─────┐                   │
│  │         Checkpoint Manager           │                   │
│  │   (Coordinates snapshots, manages    │                   │
│  │    checkpoint scheduling)            │                   │
│  └──────────────┬───────────────────────┘                   │
│                 │                                           │
│  ┌──────────────┴───────────────────────┐                   │
│  │        Checkpoint Storage            │                   │
│  │  (Distributed: S3, GCS, HDFS, NFS)   │                   │
│  └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Implementation

```python
# checkpoint_restart.py
"""
Checkpoint and Restart Fault Tolerance Mechanism
Provides crash recovery through periodic state snapshots
"""

import json
import pickle
import hashlib
import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path
import fcntl
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint"""
    checkpoint_id: str
    timestamp: float
    sequence_number: int
    state_hash: str
    process_id: str
    checkpoint_size_bytes: int
    application_version: str
    

class CheckpointManager:
    """
    Manages checkpoint lifecycle: creation, storage, and recovery
    """
    
    def __init__(self, 
                 checkpoint_dir: str = "/tmp/checkpoints",
                 checkpoint_interval_seconds: int = 30,
                 max_checkpoints_to_keep: int = 5):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_interval = checkpoint_interval_seconds
        self.max_checkpoints = max_checkpoints_to_keep
        self.sequence_number = 0
        self.last_checkpoint_time = 0
        self._checkpoint_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        
    def create_checkpoint(self, 
                         state: Dict[str, Any], 
                         process_id: str,
                         application_version: str = "1.0.0") -> CheckpointMetadata:
        """
        Create a consistent checkpoint of the current state
        
        Implements:
        - Atomic write (write to temp file, then rename)
        - Checksum verification (SHA-256)
        - Metadata tracking
        """
        with self._state_lock:
            self.sequence_number += 1
            checkpoint_id = f"chkpt_{process_id}_{self.sequence_number}_{int(time.time())}"
            
            # Serialize state
            state_bytes = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
            state_hash = hashlib.sha256(state_bytes).hexdigest()
            
            # Prepare checkpoint data
            checkpoint_data = {
                'metadata': {
                    'checkpoint_id': checkpoint_id,
                    'timestamp': time.time(),
                    'sequence_number': self.sequence_number,
                    'state_hash': state_hash,
                    'process_id': process_id,
                    'checkpoint_size_bytes': len(state_bytes),
                    'application_version': application_version
                },
                'state': state
            }
            
            # Atomic write: write to temp file, then rename
            temp_file = self.checkpoint_dir / f"{checkpoint_id}.tmp"
            final_file = self.checkpoint_dir / f"{checkpoint_id}.chkpt"
            
            try:
                with open(temp_file, 'wb') as f:
                    # Lock file during write to prevent corruption
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    pickle.dump(checkpoint_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                # Atomic rename guarantees consistency
                temp_file.rename(final_file)
                
                logger.info(f"Checkpoint created: {checkpoint_id} "
                           f"(size: {len(state_bytes)} bytes, hash: {state_hash[:16]}...)")
                
                # Cleanup old checkpoints
                self._cleanup_old_checkpoints()
                
                self.last_checkpoint_time = time.time()
                return CheckpointMetadata(**checkpoint_data['metadata'])
                
            except Exception as e:
                logger.error(f"Checkpoint creation failed: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise
    
    def restore_checkpoint(self, checkpoint_id: Optional[str] = None) -> tuple[Dict[str, Any], CheckpointMetadata]:
        """
        Restore state from a checkpoint
        
        If checkpoint_id is None, restores from the most recent valid checkpoint
        """
        if checkpoint_id is None:
            # Find most recent checkpoint
            checkpoints = list(self.checkpoint_dir.glob("*.chkpt"))
            if not checkpoints:
                raise FileNotFoundError("No checkpoints found for recovery")
            
            # Sort by modification time (most recent first)
            checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            checkpoint_file = checkpoints[0]
        else:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.chkpt"
            if not checkpoint_file.exists():
                raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")
        
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            metadata = CheckpointMetadata(**checkpoint_data['metadata'])
            state = checkpoint_data['state']
            
            # Verify integrity
            state_bytes = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
            computed_hash = hashlib.sha256(state_bytes).hexdigest()
            
            if computed_hash != metadata.state_hash:
                raise ValueError(f"Checkpoint integrity check failed: "
                               f"expected {metadata.state_hash[:16]}..., "
                               f"got {computed_hash[:16]}...")
            
            logger.info(f"Checkpoint restored: {metadata.checkpoint_id} "
                       f"(from {datetime.fromtimestamp(metadata.timestamp)})")
            
            self.sequence_number = metadata.sequence_number
            return state, metadata
            
        except Exception as e:
            logger.error(f"Checkpoint restoration failed: {e}")
            raise
    
    def start_automatic_checkpoints(self, 
                                   get_state_callback: Callable[[], Dict[str, Any]],
                                   process_id: str):
        """Start automatic checkpointing in background thread"""
        def checkpoint_worker():
            while not self._stop_event.is_set():
                try:
                    state = get_state_callback()
                    self.create_checkpoint(state, process_id)
                except Exception as e:
                    logger.error(f"Automatic checkpoint failed: {e}")
                
                # Wait for next interval or until stopped
                self._stop_event.wait(self.checkpoint_interval)
        
        self._checkpoint_thread = threading.Thread(target=checkpoint_worker, daemon=True)
        self._checkpoint_thread.start()
        logger.info(f"Automatic checkpointing started (interval: {self.checkpoint_interval}s)")
    
    def stop_automatic_checkpoints(self):
        """Stop automatic checkpointing"""
        self._stop_event.set()
        if self._checkpoint_thread:
            self._checkpoint_thread.join(timeout=5.0)
            logger.info("Automatic checkpointing stopped")
    
    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints, keeping only the most recent N"""
        checkpoints = list(self.checkpoint_dir.glob("*.chkpt"))
        if len(checkpoints) <= self.max_checkpoints:
            return
        
        # Sort by modification time (oldest first)
        checkpoints.sort(key=lambda p: p.stat().st_mtime)
        
        # Remove oldest checkpoints
        for old_checkpoint in checkpoints[:-self.max_checkpoints]:
            try:
                old_checkpoint.unlink()
                logger.debug(f"Removed old checkpoint: {old_checkpoint.name}")
            except Exception as e:
                logger.warning(f"Failed to remove old checkpoint {old_checkpoint}: {e}")


class FaultTolerantApplication:
    """
    Example application demonstrating checkpoint/restart fault tolerance
    """
    
    def __init__(self, process_id: str):
        self.process_id = process_id
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=f"/tmp/checkpoints/{process_id}",
            checkpoint_interval_seconds=10,
            max_checkpoints_to_keep=3
        )
        
        # Application state
        self.state = {
            'processed_items': 0,
            'data_buffer': [],
            'last_processed_id': None,
            'computation_results': {}
        }
        
        self.running = False
        self._state_lock = threading.Lock()
    
    def get_current_state(self) -> Dict[str, Any]:
        """Callback for checkpoint manager to capture state"""
        with self._state_lock:
            return self.state.copy()
    
    def initialize(self):
        """Initialize or recover from checkpoint"""
        try:
            recovered_state, metadata = self.checkpoint_manager.restore_checkpoint()
            self.state = recovered_state
            logger.info(f"Application recovered from checkpoint: {metadata.checkpoint_id}")
            logger.info(f"Resuming from processed_items={self.state['processed_items']}")
            return True
        except FileNotFoundError:
            logger.info("No previous checkpoint found, starting fresh")
            return False
    
    def run(self):
        """Main application loop with fault tolerance"""
        self.running = True
        
        # Start automatic checkpointing
        self.checkpoint_manager.start_automatic_checkpoints(
            self.get_current_state, 
            self.process_id
        )
        
        try:
            while self.running:
                try:
                    # Simulate work
                    self._process_next_item()
                    
                    # Simulate occasional failures for testing
                    if self.state['processed_items'] % 50 == 0 and self.state['processed_items'] > 0:
                        if os.environ.get('SIMULATE_CRASH'):
                            logger.warning("SIMULATING CRASH!")
                            raise SystemExit("Simulated crash")
                    
                    time.sleep(0.1)  # Simulate processing time
                    
                except Exception as e:
                    logger.error(f"Error during processing: {e}")
                    # Application continues - checkpoint will preserve progress
                    time.sleep(1)
                    
        finally:
            self.checkpoint_manager.stop_automatic_checkpoints()
            # Final checkpoint before shutdown
            self.checkpoint_manager.create_checkpoint(
                self.get_current_state(), 
                self.process_id
            )
    
    def _process_next_item(self):
        """Simulate processing work"""
        with self._state_lock:
            item_id = self.state['processed_items']
            
            # Simulate computation
            result = {
                'item_id': item_id,
                'timestamp': time.time(),
                'value': item_id ** 2,
                'checksum': hashlib.md5(str(item_id).encode()).hexdigest()
            }
            
            self.state['computation_results'][item_id] = result
            self.state['processed_items'] += 1
            self.state['last_processed_id'] = item_id
            
            if item_id % 10 == 0:
                logger.info(f"Processed {item_id} items")
    
    def shutdown(self):
        """Graceful shutdown"""
        self.running = False


# Demonstration
if __name__ == "__main__":
    import sys
    
    process_id = sys.argv[1] if len(sys.argv) > 1 else "worker_001"
    simulate_crash = "--simulate-crash" in sys.argv
    
    if simulate_crash:
        os.environ['SIMULATE_CRASH'] = '1'
    
    app = FaultTolerantApplication(process_id)
    
    # Try to recover
    recovered = app.initialize()
    
    try:
        logger.info(f"Starting application (recovered={recovered})...")
        app.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        app.shutdown()
    except SystemExit:
        logger.error("Application crashed! Restart to recover from checkpoint.")
        raise
```

### 1.4 Recovery Procedure

```
Recovery Algorithm:
1. DETECT: Monitor detects process failure (heartbeat timeout)
2. LOCATE: Find most recent valid checkpoint
3. VERIFY: Validate checksum and metadata integrity
4. RESTORE: Deserialize state from checkpoint
5. RESUME: Continue execution from last checkpoint point
6. NOTIFY: Log recovery event, update monitoring
```

---

## 2. Byzantine Fault Tolerance (BFT) Mechanism

### 2.1 Fault Model

**Failure Types Addressed:**
- **Byzantine failures**: Arbitrary/malicious behavior (crash, incorrect results, conflicting information)
- **Malicious attacks**: Compromised nodes sending false data
- **Network asynchrony**: Unbounded message delays
- **Message corruption**: Tampering in transit

**Assumptions:**
- Maximum f Byzantine faulty nodes out of n total nodes (n ≥ 3f + 1)
- Honest nodes follow protocol correctly
- Digital signatures prevent forgery
- Partial synchrony: system is asynchronous but with periods of synchrony
- Independent node failures (no correlated failures)

**Security Properties:**
- **Safety**: Honest nodes agree on the same value (no two honest nodes commit different values)
- **Liveness**: All honest nodes eventually decide on a value
- **Accountability**: Byzantine behavior is detectable and attributable

### 2.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BFT Consensus Cluster                       │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Replica 1  │    │   Replica 2  │    │   Replica N  │      │
│  │   (Primary)  │    │ (Secondary)  │    │ (Secondary)  │      │
│  │              │    │              │    │              │      │
│  │ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │      │
│  │ │ PBFT     │ │◄──►│ │ PBFT     │ │◄──►│ │ PBFT     │ │      │
│  │ │ Consensus│ │    │ │ Consensus│ │    │ │ Consensus│ │      │
│  │ │ Engine   │ │    │ │ Engine   │ │    │ │ Engine   │ │      │
│  │ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │      │
│  │ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │      │
│  │ │ Signature│ │    │ │ Signature│ │    │ │ Signature│ │      │
│  │ │ Verify   │ │    │ │ Verify   │ │    │ │ Verify   │ │      │
│  │ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │              │
│  ┌──────┴───────────────────┴───────────────────┴───────┐      │
│  │              P2P Network (Gossip + P2P)              │      │
│  │         (Authenticated, Encrypted Channels)          │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  Tolerance: f < n/3 Byzantine nodes                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Implementation

```python
# byzantine_fault_tolerance.py
"""
Practical Byzantine Fault Tolerance (PBFT) Implementation
Implements consensus in presence of Byzantine (arbitrary) failures
"""

import hashlib
import json
import time
import threading
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import secrets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    REQUEST = "REQUEST"
    PRE_PREPARE = "PRE_PREPARE"
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    REPLY = "REPLY"
    VIEW_CHANGE = "VIEW_CHANGE"
    NEW_VIEW = "NEW_VIEW"


@dataclass
class Message:
    """Base message structure for PBFT protocol"""
    msg_type: MessageType
    view_number: int
    sequence_number: int
    digest: str
    data: Any
    sender_id: str
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None  # In production: ECDSA signature
    
    def compute_digest(self) -> str:
        """Compute cryptographic digest of message content"""
        content = f"{self.msg_type.value}:{self.view_number}:{self.sequence_number}:{json.dumps(self.data, sort_keys=True)}:{self.sender_id}:{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            'msg_type': self.msg_type.value,
            'view_number': self.view_number,
            'sequence_number': self.sequence_number,
            'digest': self.digest,
            'data': self.data,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'signature': self.signature
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Message':
        return cls(
            msg_type=MessageType(d['msg_type']),
            view_number=d['view_number'],
            sequence_number=d['sequence_number'],
            digest=d['digest'],
            data=d['data'],
            sender_id=d['sender_id'],
            timestamp=d['timestamp'],
            signature=d.get('signature')
        )


@dataclass
class PBFTLogEntry:
    """Log entry for PBFT protocol state"""
    sequence_number: int
    view_number: int
    request_data: Any
    pre_prepare: Optional[Message] = None
    prepares: Dict[str, Message] = field(default_factory=dict)
    commits: Dict[str, Message] = field(default_factory=dict)
    committed: bool = False
    pre_prepared: bool = False


class ByzantineReplica:
    """
    PBFT Replica Node
    Implements Practical Byzantine Fault Tolerance consensus
    """
    
    def __init__(self, 
                 replica_id: str,
                 all_replicas: List[str],
                 f: int,  # Maximum number of Byzantine faults tolerated
                 view_timeout: float = 5.0):
        self.replica_id = replica_id
        self.all_replicas = sorted(all_replicas)
        self.n = len(all_replicas)
        self.f = f
        self.quorum_size = 2 * f + 1  # Minimum for consensus
        self.view_timeout = view_timeout
        
        # PBFT state
        self.view_number = 0
        self.sequence_number = 0
        self.is_primary = (self._get_primary_id() == replica_id)
        
        # Message logs
        self.log: Dict[int, PBFTLogEntry] = {}
        self.checkpoint_log: Dict[int, int] = {}  # sequence_num -> number of stable checkpoints
        self.last_stable_checkpoint = 0
        
        # View change state
        self.view_change_in_progress = False
        self.view_change_messages: Dict[int, List[Message]] = defaultdict(list)
        self.prepared_certificates: Dict[int, Any] = {}
        
        # Request handling
        self.pending_requests: Dict[str, Any] = {}
        self.client_replies: Dict[str, Message] = {}
        
        # Threading
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._view_change_timer: Optional[threading.Timer] = None
        
        # Message handlers (simulated network)
        self._network_callbacks: List[callable] = []
        
        logger.info(f"Replica {replica_id} initialized (f={f}, n={self.n}, quorum={self.quorum_size})")
    
    def _get_primary_id(self) -> str:
        """Determine primary for current view"""
        return self.all_replicas[self.view_number % self.n]
    
    def _is_valid_digest(self, digest: str, data: Any) -> bool:
        """Verify message digest"""
        content = json.dumps(data, sort_keys=True)
        expected = hashlib.sha256(content.encode()).hexdigest()
        return digest == expected
    
    def _sign_message(self, message: Message) -> str:
        """
        Create cryptographic signature for message
        In production: Use ECDSA or Ed25519
        """
        content = f"{message.msg_type.value}:{message.view_number}:{message.sequence_number}:{message.digest}:{message.sender_id}"
        # Simulated signature: HMAC with node's secret key
        secret = f"secret_key_{self.replica_id}"
        return hashlib.sha256((content + secret).encode()).hexdigest()
    
    def _verify_signature(self, message: Message) -> bool:
        """Verify message signature"""
        # In production: Verify using sender's public key
        expected = self._sign_message(message)
        return message.signature == expected
    
    def handle_client_request(self, client_id: str, operation: Dict) -> Optional[Message]:
        """
        Client sends request to replicas
        Primary receives and initiates consensus
        """
        with self._lock:
            # Generate unique request ID
            request_id = hashlib.sha256(
                f"{client_id}:{json.dumps(operation, sort_keys=True)}:{time.time()}".encode()
            ).hexdigest()[:16]
            
            if self.is_primary:
                # Primary: Initiate consensus
                return self._initiate_consensus(request_id, client_id, operation)
            else:
                # Non-primary: Forward to primary
                self.pending_requests[request_id] = {
                    'client_id': client_id,
                    'operation': operation,
                    'timestamp': time.time()
                }
                logger.debug(f"Non-primary {self.replica_id} forwarding request {request_id} to primary")
                return None
    
    def _initiate_consensus(self, request_id: str, client_id: str, operation: Dict) -> Message:
        """Primary initiates the three-phase consensus protocol"""
        with self._lock:
            self.sequence_number += 1
            seq_num = self.sequence_number
            
            # Create PRE-PREPARE message
            data = {
                'request_id': request_id,
                'client_id': client_id,
                'operation': operation,
                'timestamp': time.time()
            }
            
            digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            
            pre_prepare = Message(
                msg_type=MessageType.PRE_PREPARE,
                view_number=self.view_number,
                sequence_number=seq_num,
                digest=digest,
                data=data,
                sender_id=self.replica_id
            )
            pre_prepare.signature = self._sign_message(pre_prepare)
            
            # Log pre-prepare
            entry = PBFTLogEntry(
                sequence_number=seq_num,
                view_number=self.view_number,
                request_data=data
            )
            entry.pre_prepare = pre_prepare
            self.log[seq_num] = entry
            
            logger.info(f"Primary {self.replica_id} initiated consensus for seq={seq_num}, request={request_id}")
            
            # Broadcast PRE-PREPARE to all replicas
            self._broadcast(pre_prepare)
            
            return pre_prepare
    
    def handle_message(self, message: Message) -> Optional[Message]:
        """
        Main message handler - implements PBFT protocol logic
        """
        # Verify signature
        if not self._verify_signature(message):
            logger.warning(f"Invalid signature from {message.sender_id}, dropping message")
            return None
        
        with self._lock:
            if message.msg_type == MessageType.PRE_PREPARE:
                return self._handle_pre_prepare(message)
            elif message.msg_type == MessageType.PREPARE:
                return self._handle_prepare(message)
            elif message.msg_type == MessageType.COMMIT:
                return self._handle_commit(message)
            elif message.msg_type == MessageType.VIEW_CHANGE:
                return self._handle_view_change(message)
            elif message.msg_type == MessageType.NEW_VIEW:
                return self._handle_new_view(message)
            
        return None
    
    def _handle_pre_prepare(self, msg: Message) -> Optional[Message]:
        """
        Phase 1: Accept PRE-PREPARE from primary
        Replica validates and sends PREPARE
        """
        # Verify primary
        expected_primary = self._get_primary_id()
        if msg.sender_id != expected_primary:
            logger.warning(f"PRE-PREPARE from non-primary {msg.sender_id}, expected {expected_primary}")
            return None
        
        # Verify view number
        if msg.view_number != self.view_number:
            logger.warning(f"PRE-PREPARE for wrong view: {msg.view_number} vs {self.view_number}")
            return None
        
        # Verify digest
        if not self._is_valid_digest(msg.digest, msg.data):
            logger.warning("PRE-PREPARE digest mismatch")
            return None
        
        # Check for duplicate sequence numbers
        if msg.sequence_number in self.log:
            existing = self.log[msg.sequence_number]
            if existing.pre_prepare and existing.pre_prepare.digest != msg.digest:
                logger.error(f"Conflicting PRE-PREPARE for seq {msg.sequence_number}!")
                # This indicates a Byzantine primary - trigger view change
                self._start_view_change()
                return None
        
        # Accept PRE-PREPARE
        entry = self.log.get(msg.sequence_number, PBFTLogEntry(
            sequence_number=msg.sequence_number,
            view_number=self.view_number,
            request_data=msg.data
        ))
        entry.pre_prepare = msg
        self.log[msg.sequence_number] = entry
        
        # Send PREPARE
        prepare = Message(
            msg_type=MessageType.PREPARE,
            view_number=self.view_number,
            sequence_number=msg.sequence_number,
            digest=msg.digest,
            data={'request_id': msg.data.get('request_id')},
            sender_id=self.replica_id
        )
        prepare.signature = self._sign_message(prepare)
        
        logger.debug(f"Replica {self.replica_id} sent PREPARE for seq={msg.sequence_number}")
        self._broadcast(prepare)
        
        return prepare
    
    def _handle_prepare(self, msg: Message) -> Optional[Message]:
        """
        Phase 2: Collect PREPARE messages
        When quorum reached, send COMMIT
        """
        # Validate
        if msg.view_number != self.view_number:
            return None
        
        if msg.sequence_number not in self.log:
            return None
        
        entry = self.log[msg.sequence_number]
        
        # Verify digest matches pre-prepare
        if entry.pre_prepare and entry.pre_prepare.digest != msg.digest:
            return None
        
        # Record prepare
        entry.prepares[msg.sender_id] = msg
        
        # Check if prepared (2f prepares from different replicas + pre-prepare)
        prepare_count = len(entry.prepares)
        if prepare_count >= 2 * self.f and not entry.pre_prepared:
            entry.pre_prepared = True
            
            # Send COMMIT
            commit = Message(
                msg_type=MessageType.COMMIT,
                view_number=self.view_number,
                sequence_number=msg.sequence_number,
                digest=msg.digest,
                data={'request_id': entry.request_data.get('request_id')},
                sender_id=self.replica_id
            )
            commit.signature = self._sign_message(commit)
            
            logger.info(f"Replica {self.replica_id} reached PREPARED for seq={msg.sequence_number} "
                       f"({prepare_count} prepares)")
            self._broadcast(commit)
            
            return commit
        
        return None
    
    def _handle_commit(self, msg: Message) -> Optional[Message]:
        """
        Phase 3: Collect COMMIT messages
        When quorum reached, execute and reply
        """
        if msg.view_number != self.view_number:
            return None
        
        if msg.sequence_number not in self.log:
            return None
        
        entry = self.log[msg.sequence_number]
        
        # Verify digest
        if entry.pre_prepare and entry.pre_prepare.digest != msg.digest:
            return None
        
        # Record commit
        entry.commits[msg.sender_id] = msg
        
        # Check if committed (2f+1 commits from different replicas)
        commit_count = len(entry.commits)
        if commit_count >= self.quorum_size and not entry.committed:
            entry.committed = True
            
            # Execute operation
            result = self._execute_operation(entry.request_data)
            
            # Send REPLY to client
            reply = Message(
                msg_type=MessageType.REPLY,
                view_number=self.view_number,
                sequence_number=msg.sequence_number,
                digest=msg.digest,
                data={
                    'request_id': entry.request_data.get('request_id'),
                    'result': result,
                    'replica_id': self.replica_id
                },
                sender_id=self.replica_id
            )
            reply.signature = self._sign_message(reply)
            
            logger.info(f"Replica {self.replica_id} COMMITTED seq={msg.sequence_number} "
                       f"({commit_count} commits)")
            
            return reply
        
        return None
    
    def _execute_operation(self, request_data: Dict) -> Any:
        """Execute the client operation (deterministic)"""
        operation = request_data.get('operation', {})
        op_type = operation.get('type')
        
        if op_type == 'write':
            key = operation.get('key')
            value = operation.get('value')
            logger.info(f"Executed WRITE: {key}={value}")
            return {'status': 'success', 'key': key, 'value': value}
        
        elif op_type == 'read':
            key = operation.get('key')
            logger.info(f"Executed READ: {key}")
            return {'status': 'success', 'key': key, 'value': f"value_for_{key}"}
        
        return {'status': 'error', 'message': 'Unknown operation'}
    
    def _start_view_change(self):
        """Initiate view change protocol"""
        if self.view_change_in_progress:
            return
        
        self.view_change_in_progress = True
        self.view_number += 1
        self.is_primary = (self._get_primary_id() == self.replica_id)
        
        # Send VIEW-CHANGE message
        vc_msg = Message(
            msg_type=MessageType.VIEW_CHANGE,
            view_number=self.view_number,
            sequence_number=self.last_stable_checkpoint,
            digest='',
            data={
                'last_stable_checkpoint': self.last_stable_checkpoint,
                'prepared_certificates': self._get_prepared_certificates()
            },
            sender_id=self.replica_id
        )
        vc_msg.signature = self._sign_message(vc_msg)
        
        self.view_change_messages[self.view_number].append(vc_msg)
        self._broadcast(vc_msg)
        
        logger.warning(f"Replica {self.replica_id} started VIEW CHANGE to view {self.view_number}")
    
    def _handle_view_change(self, msg: Message) -> Optional[Message]:
        """Handle view change messages"""
        if msg.view_number <= self.view_number:
            return None
        
        self.view_change_messages[msg.view_number].append(msg)
        
        # If new primary and have enough view-change messages
        if (self.replica_id == self.all_replicas[msg.view_number % self.n] and
            len(self.view_change_messages[msg.view_number]) >= self.quorum_size):
            
            # Send NEW-VIEW
            new_view = Message(
                msg_type=MessageType.NEW_VIEW,
                view_number=msg.view_number,
                sequence_number=0,
                digest='',
                data={
                    'view_change_messages': [m.to_dict() for m in self.view_change_messages[msg.view_number]]
                },
                sender_id=self.replica_id
            )
            new_view.signature = self._sign_message(new_view)
            
            self._broadcast(new_view)
            return new_view
        
        return None
    
    def _handle_new_view(self, msg: Message):
        """Handle new view announcement"""
        if msg.view_number != self.view_number + 1:
            return None
        
        # Verify new primary
        expected_primary = self.all_replicas[msg.view_number % self.n]
        if msg.sender_id != expected_primary:
            return None
        
        # Update state
        self.view_number = msg.view_number
        self.is_primary = (self._get_primary_id() == self.replica_id)
        self.view_change_in_progress = False
        
        logger.info(f"Replica {self.replica_id} adopted NEW VIEW {self.view_number}, "
                   f"primary={self._get_primary_id()}")
    
    def _get_prepared_certificates(self) -> Dict:
        """Get prepared certificates for view change"""
        certs = {}
        for seq, entry in self.log.items():
            if entry.pre_prepared and not entry.committed:
                certs[seq] = {
                    'pre_prepare': entry.pre_prepare.to_dict() if entry.pre_prepare else None,
                    'prepares': {k: v.to_dict() for k, v in entry.prepares.items()}
                }
        return certs
    
    def _broadcast(self, message: Message):
        """Simulated broadcast to all replicas"""
        # In production: Use actual network layer (gossip, broadcast)
        for callback in self._network_callbacks:
            callback(message, self.replica_id)
    
    def register_network_callback(self, callback):
        """Register callback for network messages"""
        self._network_callbacks.append(callback)
    
    def get_status(self) -> Dict:
        """Get current replica status"""
        with self._lock:
            return {
                'replica_id': self.replica_id,
                'view_number': self.view_number,
                'is_primary': self.is_primary,
                'sequence_number': self.sequence_number,
                'committed_operations': sum(1 for e in self.log.values() if e.committed),
                'pending_operations': len(self.pending_requests)
            }


class BFTCluster:
    """Simulates a BFT cluster with multiple replicas"""
    
    def __init__(self, num_replicas: int = 4, f: int = 1):
        self.n = num_replicas
        self.f = f
        self.replicas: Dict[str, ByzantineReplica] = {}
        self.message_queue: List[Tuple[Message, str]] = []
        self._lock = threading.Lock()
        
        # Create replicas
        replica_ids = [f"replica_{i}" for i in range(num_replicas)]
        for rep_id in replica_ids:
            replica = ByzantineReplica(rep_id, replica_ids, f)
            replica.register_network_callback(self._deliver_message)
            self.replicas[rep_id] = replica
    
    def _deliver_message(self, message: Message, sender_id: str):
        """Deliver message to all other replicas"""
        with self._lock:
            self.message_queue.append((message, sender_id))
    
    def process_message_queue(self):
        """Process all pending messages"""
        with self._lock:
            queue = self.message_queue[:]
            self.message_queue = []
        
        for message, sender_id in queue:
            for replica_id, replica in self.replicas.items():
                if replica_id != sender_id:  # Don't send to self
                    replica.handle_message(message)
    
    def submit_request(self, client_id: str, operation: Dict) -> List[Message]:
        """Submit a client request to the cluster"""
        # Send to primary
        primary_id = self.replicas[f"replica_0"]._get_primary_id()
        primary = self.replicas[primary_id]
        
        result = primary.handle_client_request(client_id, operation)
        
        # Process messages until consensus
        max_iterations = 100
        for _ in range(max_iterations):
            self.process_message_queue()
            if self._is_committed(operation):
                break
        
        return result
    
    def _is_committed(self, operation: Dict) -> bool:
        """Check if operation is committed by quorum"""
        committed_count = 0
        for replica in self.replicas.values():
            for entry in replica.log.values():
                if (entry.committed and 
                    entry.request_data.get('operation') == operation):
                    committed_count += 1
                    break
        return committed_count >= self.f * 2 + 1
    
    def simulate_byzantine_behavior(self, replica_id: str, behavior: str):
        """
        Simulate Byzantine behavior for testing
        behaviors: 'silent', 'wrong_digest', 'conflicting_preprepare'
        """
        logger.warning(f"Simulating Byzantine behavior '{behavior}' on {replica_id}")
        # Implementation would modify the replica to exhibit faulty behavior
        pass
    
    def get_cluster_status(self) -> Dict:
        """Get status of all replicas"""
        return {rid: rep.get_status() for rid, rep in self.replicas.items()}


# Demonstration
if __name__ == "__main__":
    print("=" * 70)
    print("BYZANTINE FAULT TOLERANCE (PBFT) DEMONSTRATION")
    print("=" * 70)
    
    # Create 4-node cluster (tolerates 1 Byzantine fault)
    cluster = BFTCluster(num_replicas=4, f=1)
    
    print("\n1. Initial Cluster Status:")
    for rid, status in cluster.get_cluster_status().items():
        print(f"   {rid}: view={status['view_number']}, primary={status['is_primary']}")
    
    print("\n2. Submitting write operation...")
    result = cluster.submit_request(
        client_id="client_1",
        operation={'type': 'write', 'key': 'account_balance', 'value': 1000}
    )
    
    print("\n3. Checking commitment...")
    status = cluster.get_cluster_status()
    for rid, rep_status in status.items():
        print(f"   {rid}: committed_ops={rep_status['committed_operations']}")
    
    print("\n4. Submitting read operation...")
    cluster.submit_request(
        client_id="client_1",
        operation={'type': 'read', 'key': 'account_balance'}
    )
    
    print("\n5. Final Status:")
    for rid, rep_status in cluster.get_cluster_status().items():
        print(f"   {rid}: view={rep_status['view_number']}, "
              f"seq={rep_status['sequence_number']}, "
              f"committed={rep_status['committed_operations']}")
    
    print("\n" + "=" * 70)
    print("BFT consensus achieved despite potential Byzantine faults!")
    print("=" * 70)
```

---

## 3. Self-Healing Networks Mechanism

### 3.1 Fault Model

**Failure Types Addressed:**
- **Link failures**: Network partitions, cable cuts, interface failures
- **Node failures**: Router/switch crashes, power loss, software bugs
- **Degradation**: Gradual performance decay (congestion, packet loss)
- **Congestion collapse**: Feed-forward network overload
- **Configuration errors**: Human-induced routing loops, blackholes
- **Security attacks**: DDoS, routing table poisoning

**Assumptions:**
- Partial connectivity remains during failures (no total partition)
- Nodes can detect local failures (heartbeat, link-state monitoring)
- Redundant paths exist in the network topology
- Software-defined control plane enables reconfiguration
- Local recovery is faster than global convergence

**Healing Principles:**
- **Autonomic**: Self-configuring, self-optimizing, self-healing
- **Localized**: Contain failures, prevent cascade
- **Proactive**: Detect and mitigate before user impact
- **Adaptive**: Learn from failures, improve resilience

### 3.2 Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    Self-Healing Network Controller                 │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Monitoring Plane                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ Health Probes│  │  Telemetry   │  │ Anomaly Detector │  │  │
│  │  │  (Heartbeats)│  │  Collector   │  │   (ML-based)     │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │  │
│  │         └─────────────────┴───────────────────┘            │  │
│  └───────────────────────────┬─────────────────────────────────┘  │
│                              │                                     │
│  ┌───────────────────────────┴─────────────────────────────────┐  │
│  │                    Decision Plane                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ Root Cause   │  │ Healing      │  │ Policy Engine    │  │  │
│  │  │ Analyzer     │  │ Planner      │  │ (Constraints)    │  │  │
│  │  │ (Dependency  │  │ (Action      │  │                  │  │  │
│  │  │  Graph)      │  │  Selection)  │  │                  │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │  │
│  │         └─────────────────┴───────────────────┘            │  │
│  └───────────────────────────┬─────────────────────────────────┘  │
│                              │                                     │
│  ┌───────────────────────────┴─────────────────────────────────┐  │
│  │                    Action Plane                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │ Route        │  │ Traffic      │  │ Node Recovery    │  │  │
│  │  │ Recalculator │  │ Engineering  │  │ Manager          │  │  │
│  │  │ (Graph Alg)  │  │ (Load Bal)   │  │ (Restart/Replace)│  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────┴────┐           ┌────┴────┐           ┌────┴────┐
   │ Node A  │◄─────────►│ Node B  │◄─────────►│ Node C  │
   │(Router) │   Link 1  │(Router) │   Link 2  │(Router) │
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                    Alternative Paths (Backup Links)
```

### 3.3 Implementation

```python
# self_healing_network.py
"""
Self-Healing Network Controller
Implements autonomic healing for network failures
"""

import heapq
import random
import time
import threading
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


class LinkStatus(Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class NetworkNode:
    """Represents a network node (router, switch, host)"""
    node_id: str
    status: NodeStatus = NodeStatus.HEALTHY
    capacity: float = 1000.0  # Mbps
    current_load: float = 0.0
    failure_probability: float = 0.001
    last_heartbeat: float = field(default_factory=time.time)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_alive(self, timeout: float = 5.0) -> bool:
        return (time.time() - self.last_heartbeat) < timeout
    
    def get_available_capacity(self) -> float:
        return max(0, self.capacity - self.current_load)
    
    def health_score(self) -> float:
        """Compute health score (0-1)"""
        if self.status == NodeStatus.FAILED:
            return 0.0
        
        load_factor = 1.0 - (self.current_load / self.capacity)
        heartbeat_factor = min(1.0, 5.0 / (time.time() - self.last_heartbeat + 0.1))
        
        return (load_factor * 0.5 + heartbeat_factor * 0.5)


@dataclass
class NetworkLink:
    """Represents a network link between two nodes"""
    link_id: str
    source: str
    target: str
    status: LinkStatus = LinkStatus.UP
    bandwidth: float = 100.0  # Mbps
    latency_ms: float = 10.0
    packet_loss_rate: float = 0.0
    current_utilization: float = 0.0
    failure_probability: float = 0.0005
    last_updated: float = field(default_factory=time.time)
    
    def get_effective_bandwidth(self) -> float:
        if self.status == LinkStatus.DOWN:
            return 0.0
        return self.bandwidth * (1 - self.packet_loss_rate)
    
    def health_score(self) -> float:
        """Compute link health score (0-1)"""
        if self.status == LinkStatus.DOWN:
            return 0.0
        
        utilization_factor = 1.0 - (self.current_utilization / 0.9)  # Critical at 90%
        loss_factor = 1.0 - (self.packet_loss_rate / 0.1)  # Critical at 10%
        
        return max(0, (utilization_factor * 0.6 + loss_factor * 0.4))


class HealingAction:
    """Represents a healing action to be taken"""
    
    def __init__(self, 
                 action_type: str,
                 target: str,
                 parameters: Dict[str, Any],
                 priority: int = 5,
                 estimated_impact: float = 0.5):
        self.action_type = action_type
        self.target = target
        self.parameters = parameters
        self.priority = priority
        self.estimated_impact = estimated_impact
        self.timestamp = time.time()
        self.status = "pending"
        self.result = None
    
    def __lt__(self, other):
        return self.priority < other.priority
    
    def __repr__(self):
        return f"HealingAction({self.action_type} on {self.target}, P={self.priority})"


class SelfHealingController:
    """
    Autonomic Self-Healing Network Controller
    Implements MAPE-K loop: Monitor, Analyze, Plan, Execute, Knowledge
    """
    
    def __init__(self, 
                 heartbeat_interval: float = 2.0,
                 healing_check_interval: float = 3.0,
                 convergence_threshold: float = 0.95):
        
        # Network topology
        self.nodes: Dict[str, NetworkNode] = {}
        self.links: Dict[str, NetworkLink] = {}
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        
        # Control parameters
        self.heartbeat_interval = heartbeat_interval
        self.healing_check_interval = healing_check_interval
        self.convergence_threshold = convergence_threshold
        
        # Healing state
        self.healing_queue: List[HealingAction] = []
        self.active_healing_actions: Dict[str, HealingAction] = {}
        self.healing_history: List[Dict] = []
        
        # Routing state
        self.routing_table: Dict[str, Dict[str, List[str]]] = {}  # src -> dst -> path
        self.backup_paths: Dict[Tuple[str, str], List[List[str]]] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._healing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Metrics
        self.metrics = {
            'failures_detected': 0,
            'healing_actions_executed': 0,
            'mean_time_to_detect': [],
            'mean_time_to_repair': [],
            'false_positives': 0
        }
    
    # ==================== Network Management ====================
    
    def add_node(self, node_id: str, capacity: float = 1000.0) -> NetworkNode:
        """Add a node to the network"""
        with self._lock:
            node = NetworkNode(node_id=node_id, capacity=capacity)
            self.nodes[node_id] = node
            logger.info(f"Added node: {node_id} (capacity={capacity}Mbps)")
            return node
    
    def add_link(self, 
                 link_id: str, 
                 source: str, 
                 target: str, 
                 bandwidth: float = 100.0,
                 latency_ms: float = 10.0) -> NetworkLink:
        """Add a bidirectional link between nodes"""
        with self._lock:
            if source not in self.nodes or target not in self.nodes:
                raise ValueError("Both source and target nodes must exist")
            
            link = NetworkLink(
                link_id=link_id,
                source=source,
                target=target,
                bandwidth=bandwidth,
                latency_ms=latency_ms
            )
            self.links[link_id] = link
            self.adjacency_list[source].append(target)
            self.adjacency_list[target].append(source)
            
            logger.info(f"Added link: {link_id} ({source}<->{target}, {bandwidth}Mbps)")
            return link
    
    def remove_link(self, link_id: str):
        """Remove a link from the network"""
        with self._lock:
            if link_id not in self.links:
                return
            
            link = self.links[link_id]
            self.adjacency_list[link.source].remove(link.target)
            self.adjacency_list[link.target].remove(link.source)
            del self.links[link_id]
            
            logger.info(f"Removed link: {link_id}")
            self._trigger_routing_recalculation()
    
    def simulate_failure(self, target_id: str, failure_type: str = "crash"):
        """
        Simulate a failure for testing
        failure_type: 'crash', 'degradation', 'link_down', 'congestion'
        """
        with self._lock:
            if target_id in self.nodes:
                node = self.nodes[target_id]
                if failure_type == "crash":
                    node.status = NodeStatus.FAILED
                    logger.warning(f"SIMULATION: Node {target_id} CRASHED")
                elif failure_type == "degradation":
                    node.status = NodeStatus.DEGRADED
                    node.capacity *= 0.5
                    logger.warning(f"SIMULATION: Node {target_id} DEGRADED")
            
            elif target_id in self.links:
                link = self.links[target_id]
                if failure_type == "link_down":
                    link.status = LinkStatus.DOWN
                    link.current_utilization = 0
                    logger.warning(f"SIMULATION: Link {target_id} DOWN")
                elif failure_type == "congestion":
                    link.status = LinkStatus.DEGRADED
                    link.current_utilization = 0.95
                    link.packet_loss_rate = 0.15
                    logger.warning(f"SIMULATION: Link {target_id} CONGESTED")
    
    def recover_node(self, node_id: str):
        """Manually recover a failed node"""
        with self._lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.status = NodeStatus.RECOVERING
                node.last_heartbeat = time.time()
                logger.info(f"Node {node_id} recovering...")
                
                # Simulate recovery time
                threading.Timer(2.0, lambda: self._complete_recovery(node_id)).start()
    
    def _complete_recovery(self, node_id: str):
        """Complete node recovery"""
        with self._lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.status = NodeStatus.HEALTHY
                node.capacity = 1000.0  # Restore capacity
                node.current_load = 0
                logger.info(f"Node {node_id} fully recovered")
                self._trigger_routing_recalculation()
    
    # ==================== Monitoring (MAPE-K: Monitor) ====================
    
    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self._collect_telemetry()
                self._detect_anomalies()
                self._update_health_scores()
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            self._stop_event.wait(self.heartbeat_interval)
    
    def _collect_telemetry(self):
        """Collect metrics from all nodes and links"""
        with self._lock:
            for node in self.nodes.values():
                # Simulate metric collection
                node.last_heartbeat = time.time()
                node.metrics['cpu_util'] = random.uniform(0.2, 0.8)
                node.metrics['memory_util'] = random.uniform(0.3, 0.7)
                node.current_load = node.capacity * random.uniform(0.1, 0.6)
            
            for link in self.links.values():
                if link.status == LinkStatus.UP:
                    link.current_utilization = random.uniform(0.1, 0.8)
                    link.packet_loss_rate = max(0, random.gauss(0.001, 0.005))
    
    def _detect_anomalies(self):
        """Detect failures and anomalies using multiple techniques"""
        with self._lock:
            # Check for node failures (heartbeat timeout)
            for node_id, node in self.nodes.items():
                if not node.is_alive(timeout=5.0) and node.status != NodeStatus.FAILED:
                    logger.warning(f"Node {node_id} heartbeat timeout detected!")
                    node.status = NodeStatus.FAILED
                    self.metrics['failures_detected'] += 1
                    self._create_healing_action('isolate_node', node_id, priority=1)
            
            # Check for link failures
            for link_id, link in self.links.items():
                if link.health_score() < 0.3 and link.status != LinkStatus.DOWN:
                    logger.warning(f"Link {link_id} health degraded: {link.health_score():.2f}")
                    if link.packet_loss_rate > 0.1:
                        link.status = LinkStatus.DEGRADED
                        self._create_healing_action('reroute_traffic', link_id, priority=2)
            
            # Detect congestion
            for link_id, link in self.links.items():
                if link.current_utilization > 0.85:
                    logger.warning(f"Link {link_id} congested: {link.current_utilization:.1%} utilization")
                    self._create_healing_action('load_balance', link_id, priority=3)
    
    def _update_health_scores(self):
        """Update overall network health"""
        with self._lock:
            total_health = 0
            count = 0
            
            for node in self.nodes.values():
                total_health += node.health_score()
                count += 1
            
            for link in self.links.values():
                total_health += link.health_score()
                count += 1
            
            avg_health = total_health / count if count > 0 else 0
            
            if avg_health < 0.7:
                logger.warning(f"Network health degraded: {avg_health:.2f}")
    
    # ==================== Analysis & Planning (MAPE-K: Analyze & Plan) ====================
    
    def _create_healing_action(self, action_type: str, target: str, priority: int = 5):
        """Create a healing action and add to queue"""
        action = HealingAction(
            action_type=action_type,
            target=target,
            parameters={'detected_at': time.time()},
            priority=priority
        )
        
        heapq.heappush(self.healing_queue, action)
        logger.info(f"Created healing action: {action}")
    
    def _healing_loop(self):
        """Execute healing actions"""
        while not self._stop_event.is_set():
            try:
                self._process_healing_queue()
                self._proactive_healing()
            except Exception as e:
                logger.error(f"Healing error: {e}")
            
            self._stop_event.wait(self.healing_check_interval)
    
    def _process_healing_queue(self):
        """Process pending healing actions"""
        with self._lock:
            while self.healing_queue:
                action = heapq.heappop(self.healing_queue)
                
                if action.target in self.active_healing_actions:
                    continue  # Skip if already healing
                
                self.active_healing_actions[action.target] = action
                
                # Execute action
                logger.info(f"Executing: {action}")
                self._execute_healing_action(action)
    
    def _execute_healing_action(self, action: HealingAction):
        """Execute a specific healing action"""
        try:
            if action.action_type == 'isolate_node':
                self._heal_isolate_node(action)
            elif action.action_type == 'reroute_traffic':
                self._heal_reroute_traffic(action)
            elif action.action_type == 'load_balance':
                self._heal_load_balance(action)
            elif action.action_type == 'restart_node':
                self._heal_restart_node(action)
            elif action.action_type == 'update_routing':
                self._heal_update_routing(action)
            
            action.status = "completed"
            self.metrics['healing_actions_executed'] += 1
            
        except Exception as e:
            logger.error(f"Healing action failed: {e}")
            action.status = "failed"
            action.result = str(e)
        
        finally:
            if action.target in self.active_healing_actions:
                del self.active_healing_actions[action.target]
            
            self.healing_history.append({
                'action': action.action_type,
                'target': action.target,
                'status': action.status,
                'timestamp': time.time()
            })
    
    def _heal_isolate_node(self, action: HealingAction):
        """Isolate a failed node and reroute traffic"""
        node_id = action.target
        
        # Find all links connected to this node
        affected_links = [lid for lid, link in self.links.items() 
                         if link.source == node_id or link.target == node_id]
        
        # Mark links as down
        for link_id in affected_links:
            if link_id in self.links:
                self.links[link_id].status = LinkStatus.DOWN
        
        # Update adjacency list
        neighbors = list(self.adjacency_list[node_id])
        for neighbor in neighbors:
            if node_id in self.adjacency_list[neighbor]:
                self.adjacency_list[neighbor].remove(node_id)
        self.adjacency_list[node_id] = []
        
        # Trigger routing recalculation
        self._trigger_routing_recalculation()
        
        logger.info(f"Isolated node {node_id}, rerouted {len(affected_links)} links")
    
    def _heal_reroute_traffic(self, action: HealingAction):
        """Reroute traffic around a failed/degraded link"""
        link_id = action.target
        
        if link_id in self.links:
            link = self.links[link_id]
            link.status = LinkStatus.DOWN
            
            # Remove from adjacency
            if link.target in self.adjacency_list[link.source]:
                self.adjacency_list[link.source].remove(link.target)
            if link.source in self.adjacency_list[link.target]:
                self.adjacency_list[link.target].remove(link.source)
        
        self._trigger_routing_recalculation()
        logger.info(f"Rerouted traffic around link {link_id}")
    
    def _heal_load_balance(self, action: HealingAction):
        """Redistribute traffic to alleviate congestion"""
        congested_link = action.target
        
        # Find alternative paths
        if congested_link in self.links:
            link = self.links[congested_link]
            
            # Calculate alternative paths
            alt_paths = self._find_k_shortest_paths(
                link.source, 
                link.target, 
                k=3, 
                exclude_link=congested_link
            )
            
            if alt_paths:
                # Redistribute 50% of traffic to best alternative
                best_alt = alt_paths[0]
                logger.info(f"Load balancing: Shifting 50% traffic from {congested_link} to path {best_alt}")
                
                # Update link utilization
                link.current_utilization *= 0.5
    
    def _heal_restart_node(self, action: HealingAction):
        """Attempt to restart a failed node"""
        node_id = action.target
        logger.info(f"Attempting to restart node {node_id}")
        
        # Simulate restart
        threading.Timer(3.0, lambda: self.recover_node(node_id)).start()
    
    def _heal_update_routing(self, action: HealingAction):
        """Update routing tables based on current topology"""
        self._calculate_routing_tables()
        logger.info("Routing tables updated")
    
    def _proactive_healing(self):
        """Proactive measures to prevent failures"""
        with self._lock:
            # Precompute backup paths
            self._precompute_backup_paths()
            
            # Detect hotspots and redistribute
            overloaded_links = [
                link_id for link_id, link in self.links.items()
                if link.current_utilization > 0.75
            ]
            
            for link_id in overloaded_links:
                self._create_healing_action('load_balance', link_id, priority=4)
    
    # ==================== Routing Algorithms ====================
    
    def _trigger_routing_recalculation(self):
        """Trigger asynchronous routing recalculation"""
        threading.Thread(target=self._calculate_routing_tables, daemon=True).start()
    
    def _calculate_routing_tables(self):
        """Calculate shortest paths using Dijkstra's algorithm"""
        with self._lock:
            self.routing_table = {}
            
            for src in self.nodes:
                self.routing_table[src] = {}
                
                # Dijkstra's algorithm
                distances = {node: float('inf') for node in self.nodes}
                distances[src] = 0
                previous = {node: None for node in self.nodes}
                pq = [(0, src)]
                
                while pq:
                    dist, current = heapq.heappop(pq)
                    
                    if dist > distances[current]:
                        continue
                    
                    for neighbor in self.adjacency_list[current]:
                        if neighbor not in distances:
                            continue
                        
                        # Calculate edge weight (latency + congestion penalty)
                        link_key = f"{current}_{neighbor}"
                        reverse_link_key = f"{neighbor}_{current}"
                        
                        link = self.links.get(link_key) or self.links.get(reverse_link_key)
                        if not link or link.status == LinkStatus.DOWN:
                            continue
                        
                        weight = link.latency_ms + (link.current_utilization * 100)
                        
                        if distances[current] + weight < distances[neighbor]:
                            distances[neighbor] = distances[current] + weight
                            previous[neighbor] = current
                            heapq.heappush(pq, (distances[neighbor], neighbor))
                
                # Build paths
                for dst in self.nodes:
                    if dst != src and previous[dst] is not None:
                        path = []
                        current = dst
                        while current is not None:
                            path.append(current)
                            current = previous[current]
                        path.reverse()
                        self.routing_table[src][dst] = path
    
    def _find_k_shortest_paths(self, 
                               source: str, 
                               target: str, 
                               k: int = 3,
                               exclude_link: Optional[str] = None) -> List[List[str]]:
        """Find K shortest paths using Yen's algorithm"""
        paths = []
        
        # Get shortest path
        if source in self.routing_table and target in self.routing_table[source]:
            primary_path = self.routing_table[source][target]
            if primary_path:
                paths.append(primary_path)
        
        # For simplicity, return variations by excluding different links
        # In production: Implement full Yen's algorithm
        
        return paths[:k]
    
    def _precompute_backup_paths(self):
        """Precompute backup paths for critical routes"""
        self.backup_paths = {}
        
        # Identify critical node pairs (high traffic)
        critical_pairs = []
        for src in self.nodes:
            for dst in self.nodes:
                if src != dst and src in self.routing_table and dst in self.routing_table[src]:
                    critical_pairs.append((src, dst))
        
        # Precompute backups
        for src, dst in critical_pairs[:10]:  # Limit for performance
            backups = self._find_k_shortest_paths(src, dst, k=2)
            if len(backups) > 1:
                self.backup_paths[(src, dst)] = backups[1:]
    
    # ==================== Control Interface ====================
    
    def start(self):
        """Start the self-healing controller"""
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._healing_thread = threading.Thread(target=self._healing_loop, daemon=True)
        
        self._monitor_thread.start()
        self._healing_thread.start()
        
        # Initial routing calculation
        self._calculate_routing_tables()
        
        logger.info("Self-healing controller started")
    
    def stop(self):
        """Stop the controller"""
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        if self._healing_thread:
            self._healing_thread.join(timeout=5.0)
        
        logger.info("Self-healing controller stopped")
    
    def get_network_status(self) -> Dict:
        """Get comprehensive network status"""
        with self._lock:
            return {
                'nodes': {
                    nid: {
                        'status': node.status.value,
                        'health': node.health_score(),
                        'load': node.current_load,
                        'capacity': node.capacity
                    }
                    for nid, node in self.nodes.items()
                },
                'links': {
                    lid: {
                        'status': link.status.value,
                        'health': link.health_score(),
                        'utilization': link.current_utilization,
                        'bandwidth': link.bandwidth
                    }
                    for lid, link in self.links.items()
                },
                'routing_table_size': len(self.routing_table),
                'backup_paths_count': len(self.backup_paths),
                'pending_healing_actions': len(self.healing_queue),
                'active_healing_actions': len(self.active_healing_actions),
                'metrics': self.metrics.copy()
            }
    
    def get_path(self, source: str, destination: str) -> Optional[List[str]]:
        """Get current best path between two nodes"""
        with self._lock:
            if source in self.routing_table and destination in self.routing_table[source]:
                return self.routing_table[source][destination]
            return None


# Demonstration
if __name__ == "__main__":
    print("=" * 70)
    print("SELF-HEALING NETWORK CONTROLLER DEMONSTRATION")
    print("=" * 70)
    
    # Create controller
    controller = SelfHealingController(
        heartbeat_interval=1.0,
        healing_check_interval=2.0
    )
    
    # Build sample topology
    print("\n1. Building network topology...")
    
    # Add nodes
    for i in range(5):
        controller.add_node(f"router_{i}", capacity=1000.0)
    
    # Add links (mesh-like topology with redundancy)
    links = [
        ("link_0_1", "router_0", "router_1", 100),
        ("link_0_2", "router_0", "router_2", 100),
        ("link_1_2", "router_1", "router_2", 100),
        ("link_1_3", "router_1", "router_3", 100),
        ("link_2_3", "router_2", "router_3", 100),
        ("link_2_4", "router_2", "router_4", 100),
        ("link_3_4", "router_3", "router_4", 100),
        ("link_0_4", "router_0", "router_4", 50),  # Backup path
    ]
    
    for link_id, src, dst, bw in links:
        controller.add_link(link_id, src, dst, bandwidth=bw)
    
    print(f"   Added {len(controller.nodes)} nodes, {len(controller.links)} links")
    
    # Start controller
    print("\n2. Starting self-healing controller...")
    controller.start()
    time.sleep(2)
    
    # Show initial routing
    print("\n3. Initial routing paths:")
    for src in controller.nodes:
        for dst in controller.nodes:
            if src != dst:
                path = controller.get_path(src, dst)
                if path:
                    print(f"   {src} -> {dst}: {' -> '.join(path)}")
    
    # Simulate failures
    print("\n4. Simulating network failures...")
    controller.simulate_failure("link_0_1", "link_down")
    controller.simulate_failure("router_3", "crash")
    
    time.sleep(3)
    
    # Show healed routing
    print("\n5. Healed routing paths (after self-healing):")
    for src in controller.nodes:
        for dst in controller.nodes:
            if src != dst:
                path = controller.get_path(src, dst)
                if path:
                    print(f"   {src} -> {dst}: {' -> '.join(path)}")
    
    # Show status
    print("\n6. Network status:")
    status = controller.get_network_status()
    for node_id, node_status in status['nodes'].items():
        print(f"   {node_id}: {node_status['status']} (health: {node_status['health']:.2f})")
    
    print(f"\n   Healing actions executed: {status['metrics']['healing_actions_executed']}")
    print(f"   Pending actions: {status['pending_healing_actions']}")
    
    # Stop controller
    print("\n7. Stopping controller...")
    controller.stop()
    
    print("\n" + "=" * 70)
    print("Self-healing network demonstration complete!")
    print("=" * 70)
```

---

## 4. Comparative Analysis

| Mechanism | Failure Model | Overhead | Recovery Time | Complexity | Use Case |
|-----------|--------------|----------|---------------|------------|----------|
| **Checkpoint/Restart** | Crash-stop, transient | Low (periodic snapshots) | Seconds to minutes | Low | Single-node applications, databases |
| **Byzantine Fault Tolerance** | Arbitrary/malicious | High (3f+1 replicas) | Milliseconds to seconds | High | Distributed consensus, blockchains, critical infrastructure |
| **Self-Healing Networks** | Link/node failures, degradation | Medium (monitoring overhead) | Sub-second to seconds | Medium | Network infrastructure, SDN, cloud networking |

---

## 5. Integration Guidelines

### 5.1 Combining Mechanisms

```
┌─────────────────────────────────────────────────────────────┐
│           Integrated Fault Tolerance Architecture           │
│                                                             │
│  Application Layer:                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Application (with Checkpoint/Restart)              │   │
│  │  • Periodic state snapshots                         │   │
│  │  • Automatic recovery on crash                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  Distributed Consensus:                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  BFT Cluster (PBFT)                                 │   │
│  │  • 4 replicas (tolerates 1 Byzantine)               │   │
│  │  • Consensus for state machine replication          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  Network Layer:                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Self-Healing Network Controller                    │   │
│  │  • Link/node failure detection                      │   │
│  │  • Automatic rerouting and load balancing           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  Infrastructure:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Physical/Virtual Network + Compute Resources       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Monitoring and Observability

All three mechanisms should export metrics:

- **Checkpoint/Restart**: checkpoint latency, recovery time, state size
- **BFT**: consensus latency, view change frequency, Byzantine detection rate
- **Self-Healing**: MTTD (Mean Time To Detect), MTTR (Mean Time To Repair), healing success rate

---

## 6. Conclusion

This report presented three comprehensive fault tolerance mechanisms:

1. **Checkpoint and Restart**: Simple, effective for crash-stop failures with low overhead
2. **Byzantine Fault Tolerance**: Robust against arbitrary failures, essential for untrusted environments
3. **Self-Healing Networks**: Autonomic recovery for network infrastructure, proactive and adaptive

Each mechanism addresses distinct failure models and can be combined for defense in depth in complex distributed systems.

---

## Appendix: Quick Reference

### Checkpoint/Restart
- **Best for**: Stateful applications, databases, long-running computations
- **Key parameters**: Checkpoint interval, storage backend, max checkpoints retained

### Byzantine Fault Tolerance
- **Best for**: Consensus systems, multi-party computation, blockchain
- **Key constraint**: Requires n ≥ 3f + 1 replicas to tolerate f faults

### Self-Healing Networks
- **Best for**: Network infrastructure, SDN, cloud load balancers
- **Key algorithms**: Dijkstra for routing, anomaly detection, automated remediation
