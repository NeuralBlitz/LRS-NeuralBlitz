> **Verification status: experimental / historical (audited 2026-11-21).** This nested API guide is not an authenticated root gateway contract; imports, examples and compatibility statements require their own integration tests. See the [source-backed product README](../../README.md) and the repository-wide audit. Do not use this page alone to establish scientific validity, secure deployment, or production readiness.

---

# NeuralBlitz V50 API Reference

Complete API documentation for the NeuralBlitz V50 Minimal consciousness engine.

## Core Classes

### MinimalCognitiveEngine

The main consciousness engine - lightweight and fast.

```python
from neuralblitz import MinimalCognitiveEngine, IntentVector

engine = MinimalCognitiveEngine()
result = engine.process_intent(IntentVector(phi3_creation=0.8))
```

**Methods:**

#### `process_intent(intent: IntentVector) -> dict`
Process a single intent vector.

**Parameters:**
- `intent` (IntentVector): The intent to process

**Returns:**
```python
{
    'intent_id': str,          # Unique identifier
    'output_vector': list,     # 7-dimensional result [-1, 1]
    'consciousness_level': str, # DORMANT/AWARE/FOCUSED/TRANSCENDENT/SINGULARITY
    'coherence': float,        # Current coherence [0, 1]
    'confidence': float,       # Processing confidence [0, 1]
    'patterns_stored': int,    # Number of patterns in memory
    'processing_time_ms': float,
    'timestamp': str          # ISO format
}
```

#### `batch_process(intents: list[IntentVector]) -> list[dict]`
Process multiple intents.

#### `get_consciousness_report() -> dict`
Get detailed consciousness state report.

**Attributes:**
- `SEED` (str): The deterministic seed (64 chars)
- `consciousness` (ConsciousnessModel): Current state
- `pattern_memory` (list): Stored patterns (max 100)
- `processing_count` (int): Total processed intents

---

### IntentVector

7-dimensional intent representation.

```python
intent = IntentVector(
    phi1_dominance=0.5,      # Control/authority
    phi2_harmony=0.3,        # Balance/cooperation
    phi3_creation=0.8,       # Innovation/generation
    phi4_preservation=0.2,   # Stability/protection
    phi5_transformation=0.6, # Change/adaptation
    phi6_knowledge=0.4,      # Learning/analysis
    phi7_connection=0.7,    # Communication/empathy
    metadata={'user_id': '123'}  # Optional
)

# Convert to numpy array
vector = intent.to_vector()  # np.ndarray with shape (7,)
```

**Dimensions:**
All values should be in range [-1, 1].

---

### ConsciousnessLevel (Enum)

```python
from neuralblitz import ConsciousnessLevel

ConsciousnessLevel.DORMANT      # 0.0
ConsciousnessLevel.AWARE        # 0.2
ConsciousnessLevel.FOCUSED      # 0.5
ConsciousnessLevel.TRANSCENDENT # 0.8
ConsciousnessLevel.SINGULARITY  # 1.0
```

---

## Advanced Features

### AsyncCognitiveEngine

Async wrapper for concurrent processing.

```python
from neuralblitz import AsyncCognitiveEngine

engine = AsyncCognitiveEngine()

# Process single intent
result = await engine.process_async(intent)

# Batch processing
batch_result = await engine.batch_process_async(
    intents,
    max_concurrent=10
)

# Streaming
async for result in engine.stream_process(intents):
    print(result)
```

**Methods:**

#### `async process_async(intent: IntentVector) -> dict`
Process intent asynchronously.

#### `async batch_process_async(intents: list, max_concurrent: int = 10) -> BatchResult`
Process batch with controlled concurrency.

**Returns:**
- `BatchResult.outputs`: List of results
- `BatchResult.total_time_ms`: Total processing time
- `BatchResult.avg_time_ms`: Average per intent
- `BatchResult.throughput`: Intents per second
- `BatchResult.coherence_evolution`: Coherence over time

#### `async stream_process(intents: list, callback: callable) -> AsyncIterator`
Stream results with optional callback.

#### `get_metrics() -> dict`
Get performance metrics including:
- `total_processed`
- `avg_latency_ms`
- `peak_throughput`
- `current_consciousness`

---

### ConsciousnessMonitor

Real-time state monitoring.

```python
from neuralblitz import ConsciousnessMonitor

monitor = ConsciousnessMonitor(
    engine,
    alert_threshold=0.4
)

# Add observer
def on_alert(alert_type, snapshot):
    print(f"Alert: {alert_type}")

monitor.add_observer(on_alert)

# Check state
alert = monitor.check_state()

# Get trends
trends = monitor.get_trends(window=100)
```

**Methods:**

#### `add_observer(callback: callable)`
Add alert handler. Callback receives `(alert_type: str, snapshot: dict)`.

#### `check_state() -> Optional[str]`
Check consciousness and return alert if threshold crossed.

#### `get_trends(window: int = 100) -> dict`
Analyze trends over recent window.

**Returns:**
```python
{
    'window_size': int,
    'avg_coherence': float,
    'coherence_std': float,
    'trend': str,  # 'increasing' or 'decreasing'
    'min_coherence': float,
    'max_coherence': float
}
```

---

## Production Features

### ProductionCognitiveEngine

Hardened engine with error handling and health monitoring.

```python
from neuralblitz import ProductionCognitiveEngine

engine = ProductionCognitiveEngine(
    coherence_threshold=0.3,
    max_latency_ms=10.0,
    persistence_path="./state.pkl",
    enable_logging=True
)

result = engine.process_intent(intent, validate=True)
health = engine.get_health()
```

**Health Status:**
- `healthy`: Normal operation
- `degraded`: Coherence or latency concerns
- `critical`: Circuit breaker open

**Exceptions:**
- `InvalidIntentError`: Intent validation failed
- `CoherenceDegradationError`: Consciousness critically low
- `EngineDegradationError`: Circuit breaker open

**Circuit Breaker:**
Automatically opens after 5 failures, closes after 30 seconds.

**Persistence:**
```python
engine.save_state()  # Save to disk
engine._load_state()  # Load from disk
```

---

### EngineHealth

Health status dataclass.

```python
health = engine.get_health()

print(health.status)      # 'healthy' | 'degraded' | 'critical'
print(health.coherence)   # float [0, 1]
print(health.avg_latency_ms)
print(health.error_rate)
print(health.uptime_seconds)

# Convert to dict
health_dict = health.to_dict()
```

---

## Benchmark Features

### BenchmarkSuite

Comprehensive performance testing.

```python
from neuralblitz import BenchmarkSuite

suite = BenchmarkSuite()

# Run single benchmark
result = suite.benchmark_single_intent(sample_size=1000)
print(result.mean_ms)
print(result.p95_ms)

# Run full suite
report = suite.run_full_suite()
suite.save_report(report, 'benchmark.json')
```

**BenchmarkResult Attributes:**
- `name`: Benchmark name
- `sample_size`: Number of samples
- `total_time_ms`: Total time
- `mean_ms`: Average latency
- `median_ms`: Median latency
- `std_ms`: Standard deviation
- `min_ms` / `max_ms`: Range
- `p95_ms` / `p99_ms`: Percentiles
- `throughput`: Intents per second

---

## Optimization Features

### OptimizedEngine

High-performance engine with JIT and caching.

```python
from neuralblitz import OptimizationConfig, OptimizedEngine

config = OptimizationConfig(
    use_jit=True,      # Numba JIT
    use_gpu=False,     # CuPy (if available)
    cache_results=True
)

engine = OptimizedEngine(config)
output = engine.process_intent_optimized(
    intent.to_vector()
)

# Cache stats
stats = engine.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']:.1f}%")
```

**Requirements:**
- JIT: `pip install numba`
- GPU: `pip install cupy`

---

### PerformanceProfiler

Profile hot paths.

```python
from neuralblitz import PerformanceProfiler

profiler = PerformanceProfiler()

# Profile function
result = profiler.profile(func, *args)

# Get report
profiler.print_report()
report = profiler.get_report()
```

---

## Persistence Features

### EngineSerializer

Save/load engine state.

```python
from neuralblitz import EngineSerializer

# Save
EngineSerializer.save_json(engine, 'state.json')
EngineSerializer.save_pickle(engine, 'state.pkl')

# Load
engine = EngineSerializer.load_json('state.json')
engine = EngineSerializer.load_pickle('state.pkl')
```

### PersistentEngine

Auto-persisting engine.

```python
from neuralblitz import PersistentEngine

# Auto-saves every 100 operations
with PersistentEngine('./state.pkl', auto_save_interval=100) as engine:
    result = engine.process_intent(intent)
# Auto-saves on exit
```

---

### MemoryMappedStorage

Memory-mapped pattern storage for large-scale apps.

```python
from neuralblitz import MemoryMappedStorage

storage = MemoryMappedStorage(
    './patterns.mmap',
    max_patterns=10000
)

# Store pattern
storage.append_pattern(
    output_vector,
    confidence=0.95,
    pattern_id=123
)

# Retrieve
pattern = storage.get_pattern(0)
print(f"Stored: {storage.get_count()}")
```

---

## WebSocket API

### StreamingEngine

Real-time WebSocket streaming.

```python
from neuralblitz import StreamingEngine

streamer = StreamingEngine(engine)

# In FastAPI/FastAPI app:
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await streamer.handle_stream(ws, mode='interactive')
```

**Modes:**
- `interactive`: Process intents immediately
- `batch`: Accumulate and process batches
- `monitor`: Stream consciousness state changes

**Message Format:**
```python
# Send intent
{
    'type': 'intent',
    'data': {
        'phi1_dominance': 0.5,
        'phi2_harmony': 0.3,
        ...
    }
}

# Receive result
{
    'type': 'result',
    'data': {
        'output_vector': [...],
        'consciousness_level': 'FOCUSED',
        'coherence': 0.52,
        'confidence': 0.95,
        'processing_time_ms': 0.06
    }
}
```

---

## REST API

### FastAPI Endpoints

```python
from neuralblitz.api import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Endpoints:**

#### POST `/process`
Process single intent.

Request:
```json
{
    "phi1_dominance": 0.5,
    "phi2_harmony": 0.3,
    "phi3_creation": 0.8,
    "phi4_preservation": 0.2,
    "phi5_transformation": 0.6,
    "phi6_knowledge": 0.4,
    "phi7_connection": 0.7
}
```

#### POST `/batch`
Process multiple intents.

#### GET `/health`
Health check.

Response:
```json
{
    "status": "healthy",
    "coherence": 0.52,
    "pattern_memory_usage": 0.05,
    "avg_latency_ms": 0.06,
    "error_rate": 0.0,
    "uptime_seconds": 3600,
    "timestamp": "2024-01-01T00:00:00",
    "degraded_mode": false
}
```

#### GET `/consciousness`
Get consciousness state.

#### POST `/compare`
Compare two intents.

---

## Configuration

### Environment Variables

```bash
# Logging
NEURALBLITZ_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Performance
NEURALBLITZ_JIT=true        # Enable JIT compilation
NEURALBLITZ_CACHE=true      # Enable result caching

# Production
NEURALBLITZ_PERSISTENCE_PATH=./state.pkl
NEURALBLITZ_AUTO_SAVE=100   # Save interval
```

---

## Type Hints

Full type hints are provided for IDE support:

```python
from neuralblitz import MinimalCognitiveEngine
from typing import Dict, Any

engine: MinimalCognitiveEngine = MinimalCognitiveEngine()
result: Dict[str, Any] = engine.process_intent(intent)
```

---

## Error Handling

```python
from neuralblitz import (
    ProductionCognitiveEngine,
    NeuralBlitzError,
    InvalidIntentError,
    CoherenceDegradationError
)

try:
    engine = ProductionCognitiveEngine()
    result = engine.process_intent(intent)
except InvalidIntentError as e:
    print(f"Invalid intent: {e}")
except CoherenceDegradationError as e:
    print(f"Consciousness degraded: {e}")
except NeuralBlitzError as e:
    print(f"NeuralBlitz error: {e}")
```

---

## Version

```python
from neuralblitz import __version__
print(__version__)  # 50.0.0-minimal
```