#!/usr/bin/env python3
"""
TimescaleDB Agent Metrics Client
Handles writing and querying agent metrics from TimescaleDB
"""

import os
import json
import random
import psycopg2
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class AgentMetric:
    """Represents a single agent performance metric"""

    time: datetime
    agent_id: str
    agent_type: str
    host: str
    cpu_usage: float
    memory_usage_mb: float
    active_tasks: int
    task_completion_rate: float
    latency_ms: float
    error_count: int = 0
    custom_metrics: Optional[Dict] = None


@dataclass
class AgentEvent:
    """Represents an agent event"""

    time: datetime
    agent_id: str
    event_type: str
    severity: str  # info, warning, error, critical
    message: str
    metadata: Optional[Dict] = None
    trace_id: Optional[str] = None


@dataclass
class AgentState:
    """Represents agent state snapshot"""

    time: datetime
    agent_id: str
    state: str
    configuration: Optional[Dict] = None
    version: Optional[str] = None
    uptime_seconds: Optional[int] = None


class TimescaleDBAgentClient:
    """Client for interacting with TimescaleDB for agent metrics"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "agent_metrics",
        user: str = "agent_user",
        password: str = "agent_pass_123",
    ):
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self._connection = None

    def connect(self):
        """Establish database connection"""
        if not self._connection or self._connection.closed:
            self._connection = psycopg2.connect(**self.connection_params)
            self._connection.autocommit = False
        return self._connection

    def close(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()

    @contextmanager
    def cursor(self):
        """Context manager for database cursor"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def write_performance_metric(self, metric: AgentMetric) -> bool:
        """Write a single agent performance metric"""
        try:
            with self.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_metrics.agent_performance (
                        time, agent_id, agent_type, host, cpu_usage,
                        memory_usage_mb, active_tasks, task_completion_rate,
                        latency_ms, error_count, custom_metrics
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        metric.time,
                        metric.agent_id,
                        metric.agent_type,
                        metric.host,
                        metric.cpu_usage,
                        metric.memory_usage_mb,
                        metric.active_tasks,
                        metric.task_completion_rate,
                        metric.latency_ms,
                        metric.error_count,
                        json.dumps(metric.custom_metrics)
                        if metric.custom_metrics
                        else None,
                    ),
                )
            return True
        except Exception as e:
            print(f"Error writing performance metric: {e}")
            return False

    def write_batch_metrics(self, metrics: List[AgentMetric]) -> int:
        """Write multiple metrics in batch (more efficient)"""
        try:
            with self.cursor() as cur:
                args_str = ",".join(
                    [
                        cur.mogrify(
                            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                m.time,
                                m.agent_id,
                                m.agent_type,
                                m.host,
                                m.cpu_usage,
                                m.memory_usage_mb,
                                m.active_tasks,
                                m.task_completion_rate,
                                m.latency_ms,
                                m.error_count,
                                json.dumps(m.custom_metrics)
                                if m.custom_metrics
                                else None,
                            ),
                        ).decode("utf-8")
                        for m in metrics
                    ]
                )

                cur.execute(f"""
                    INSERT INTO agent_metrics.agent_performance (
                        time, agent_id, agent_type, host, cpu_usage,
                        memory_usage_mb, active_tasks, task_completion_rate,
                        latency_ms, error_count, custom_metrics
                    ) VALUES {args_str}
                """)
            return len(metrics)
        except Exception as e:
            print(f"Error writing batch metrics: {e}")
            return 0

    def write_agent_event(self, event: AgentEvent) -> bool:
        """Write an agent event"""
        try:
            with self.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_metrics.agent_events (
                        time, agent_id, event_type, severity, message,
                        metadata, trace_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        event.time,
                        event.agent_id,
                        event.event_type,
                        event.severity,
                        event.message,
                        json.dumps(event.metadata) if event.metadata else None,
                        event.trace_id,
                    ),
                )
            return True
        except Exception as e:
            print(f"Error writing agent event: {e}")
            return False

    def write_agent_state(self, state: AgentState) -> bool:
        """Write agent state snapshot"""
        try:
            with self.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_metrics.agent_state (
                        time, agent_id, state, configuration, version, uptime_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        state.time,
                        state.agent_id,
                        state.state,
                        json.dumps(state.configuration)
                        if state.configuration
                        else None,
                        state.version,
                        state.uptime_seconds,
                    ),
                )
            return True
        except Exception as e:
            print(f"Error writing agent state: {e}")
            return False

    def query_metrics(
        self,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query agent metrics with filters"""
        try:
            query = """
                SELECT 
                    time, agent_id, agent_type, host, cpu_usage,
                    memory_usage_mb, active_tasks, task_completion_rate,
                    latency_ms, error_count, custom_metrics
                FROM agent_metrics.agent_performance
                WHERE 1=1
            """
            params = []

            if agent_id:
                query += " AND agent_id = %s"
                params.append(agent_id)

            if start_time:
                query += " AND time >= %s"
                params.append(start_time)

            if end_time:
                query += " AND time <= %s"
                params.append(end_time)

            query += " ORDER BY time DESC LIMIT %s"
            params.append(limit)

            with self.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                results = []
                for row in cur.fetchall():
                    row_dict = dict(zip(columns, row))
                    if row_dict.get("custom_metrics"):
                        row_dict["custom_metrics"] = json.loads(
                            row_dict["custom_metrics"]
                        )
                    results.append(row_dict)
                return results

        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []

    def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent health status using the stored function"""
        try:
            with self.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_metrics.get_agent_health(%s)", (agent_id,)
                )
                result = cur.fetchone()
                if result:
                    return {
                        "agent_id": result[0],
                        "health_score": result[1],
                        "status": result[2],
                        "last_seen": result[3],
                    }
                return None
        except Exception as e:
            print(f"Error getting agent health: {e}")
            return None

    def get_top_problematic_agents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top problematic agents using the stored function"""
        try:
            with self.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_metrics.get_top_problematic_agents(%s)",
                    (limit,),
                )
                results = []
                for row in cur.fetchall():
                    results.append(
                        {
                            "agent_id": row[0],
                            "error_count": row[1],
                            "avg_latency_ms": row[2],
                            "incident_count": row[3],
                        }
                    )
                return results
        except Exception as e:
            print(f"Error getting problematic agents: {e}")
            return []

    def query_aggregated_metrics(
        self, time_bucket: str = "1 hour", agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query time-bucketed aggregated metrics"""
        try:
            query = f"""
                SELECT 
                    time_bucket(%s, time) as bucket,
                    agent_id,
                    avg(cpu_usage) as avg_cpu,
                    max(cpu_usage) as max_cpu,
                    avg(memory_usage_mb) as avg_memory,
                    max(memory_usage_mb) as max_memory,
                    sum(active_tasks) as total_tasks,
                    avg(latency_ms) as avg_latency,
                    sum(error_count) as total_errors
                FROM agent_metrics.agent_performance
                WHERE time > NOW() - INTERVAL '24 hours'
            """
            params = [time_bucket]

            if agent_id:
                query += " AND agent_id = %s"
                params.append(agent_id)

            query += """
                GROUP BY bucket, agent_id
                ORDER BY bucket DESC
            """

            with self.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

        except Exception as e:
            print(f"Error querying aggregated metrics: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.cursor() as cur:
                stats = {}

                # Total metrics count
                cur.execute("SELECT count(*) FROM agent_metrics.agent_performance")
                stats["total_performance_metrics"] = cur.fetchone()[0]

                # Total events count
                cur.execute("SELECT count(*) FROM agent_metrics.agent_events")
                stats["total_events"] = cur.fetchone()[0]

                # Unique agents
                cur.execute(
                    "SELECT count(DISTINCT agent_id) FROM agent_metrics.agent_performance"
                )
                stats["unique_agents"] = cur.fetchone()[0]

                # Time range
                cur.execute("""
                    SELECT 
                        min(time) as earliest,
                        max(time) as latest
                    FROM agent_metrics.agent_performance
                """)
                row = cur.fetchone()
                stats["time_range"] = {"earliest": row[0], "latest": row[1]}

                return stats
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}


def generate_sample_metrics(agent_id: str) -> AgentMetric:
    """Generate sample agent metrics"""
    agent_types = ["collector", "processor", "analyzer", "coordinator"]
    hosts = [f"host-{i}" for i in range(10)]

    return AgentMetric(
        time=datetime.now(timezone.utc),
        agent_id=agent_id,
        agent_type=random.choice(agent_types),
        host=random.choice(hosts),
        cpu_usage=random.uniform(10, 95),
        memory_usage_mb=random.uniform(512, 8192),
        active_tasks=random.randint(0, 50),
        task_completion_rate=random.uniform(0.5, 1.0),
        latency_ms=random.uniform(5, 200),
        error_count=random.randint(0, 5) if random.random() > 0.8 else 0,
        custom_metrics={
            "queue_depth": random.randint(0, 100),
            "cache_hit_rate": random.uniform(0.7, 0.99),
        },
    )


def demo_timescaledb():
    """Demonstrate TimescaleDB functionality"""
    print("Initializing TimescaleDB Agent Metrics Client...")
    client = TimescaleDBAgentClient()

    print("\nGenerating and writing sample agent metrics...")
    metrics = []
    for i in range(20):
        agent_id = f"agent-{random.randint(1, 5):03d}"
        metric = generate_sample_metrics(agent_id)
        metrics.append(metric)

    # Write in batch
    written = client.write_batch_metrics(metrics)
    print(f"  Written {written} metrics")

    # Write some events
    print("\nWriting agent events...")
    events = [
        AgentEvent(
            time=datetime.now(timezone.utc),
            agent_id="agent-001",
            event_type="started",
            severity="info",
            message="Agent initialized successfully",
            metadata={"version": "v1.0", "config": "default"},
        ),
        AgentEvent(
            time=datetime.now(timezone.utc),
            agent_id="agent-002",
            event_type="error",
            severity="error",
            message="Connection timeout",
            trace_id="trace-abc-123",
        ),
    ]

    for event in events:
        success = client.write_agent_event(event)
        print(f"  Event written: {'✓' if success else '✗'}")

    # Query metrics
    print("\nQuerying metrics for agent-001...")
    results = client.query_metrics(agent_id="agent-001", limit=5)
    print(f"  Found {len(results)} metrics")

    # Get health
    print("\nChecking agent health...")
    health = client.get_agent_health("agent-001")
    if health:
        print(f"  Agent ID: {health['agent_id']}")
        print(f"  Health Score: {health['health_score']:.2f}")
        print(f"  Status: {health['status']}")
        print(f"  Last Seen: {health['last_seen']}")

    # Get problematic agents
    print("\nTop problematic agents...")
    problematic = client.get_top_problematic_agents(limit=5)
    for agent in problematic:
        print(
            f"  {agent['agent_id']}: {agent['error_count']} errors, "
            f"{agent['avg_latency_ms']:.2f}ms avg latency"
        )

    # Get statistics
    print("\nDatabase Statistics:")
    stats = client.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    client.close()
    print("\nTimescaleDB demo completed!")


if __name__ == "__main__":
    demo_timescaledb()
