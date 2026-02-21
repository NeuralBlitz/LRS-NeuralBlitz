#!/usr/bin/env python3
"""
Prometheus Metrics Integration Client
Provides custom metrics exporters and Prometheus query integration
"""

import time
import random
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager
import threading


@dataclass
class PrometheusQueryResult:
    """Represents a Prometheus query result"""

    metric: Dict[str, str]
    value: tuple  # (timestamp, value)
    values: Optional[List[tuple]] = None  # For range queries


class PrometheusMetricsClient:
    """Client for Prometheus integration and custom metrics"""

    def __init__(
        self, prometheus_url: str = "http://localhost:9090", timeout: int = 30
    ):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.timeout = timeout
        self.metrics_buffer = []
        self._lock = threading.Lock()

    def query(
        self, query: str, time: Optional[datetime] = None
    ) -> List[PrometheusQueryResult]:
        """Execute an instant query against Prometheus"""
        try:
            params = {"query": query}
            if time:
                params["time"] = time.timestamp()

            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            if data["status"] != "success":
                raise Exception(f"Query failed: {data.get('error', 'Unknown error')}")

            results = []
            for result in data["data"]["result"]:
                results.append(
                    PrometheusQueryResult(
                        metric=result["metric"], value=result["value"], values=None
                    )
                )

            return results

        except Exception as e:
            print(f"Error querying Prometheus: {e}")
            return []

    def query_range(
        self, query: str, start: datetime, end: datetime, step: str = "15s"
    ) -> List[PrometheusQueryResult]:
        """Execute a range query against Prometheus"""
        try:
            params = {
                "query": query,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            }

            response = requests.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            if data["status"] != "success":
                raise Exception(f"Query failed: {data.get('error', 'Unknown error')}")

            results = []
            for result in data["data"]["result"]:
                results.append(
                    PrometheusQueryResult(
                        metric=result["metric"],
                        value=result["values"][0] if result["values"] else None,
                        values=result["values"],
                    )
                )

            return results

        except Exception as e:
            print(f"Error querying Prometheus range: {e}")
            return []

    def get_metric_metadata(
        self, metric: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get metadata about metrics"""
        try:
            params = {}
            if metric:
                params["metric"] = metric
            if limit:
                params["limit"] = limit

            response = requests.get(
                f"{self.prometheus_url}/api/v1/metadata",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Error getting metric metadata: {e}")
            return {}

    def get_series(
        self,
        match: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """Get time series that match label selectors"""
        try:
            params = {"match[]": match}
            if start:
                params["start"] = start.timestamp()
            if end:
                params["end"] = end.timestamp()

            response = requests.get(
                f"{self.prometheus_url}/api/v1/series",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            if data["status"] == "success":
                return data["data"]
            return []

        except Exception as e:
            print(f"Error getting series: {e}")
            return []

    def get_label_values(self, label: str) -> List[str]:
        """Get all values for a label"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/label/{label}/values",
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            if data["status"] == "success":
                return data["data"]
            return []

        except Exception as e:
            print(f"Error getting label values: {e}")
            return []


class CustomMetricsExporter:
    """Export custom metrics in Prometheus exposition format"""

    def __init__(self, registry_name: str = "neuralblitz"):
        self.registry_name = registry_name
        self.metrics = {}
        self._lock = threading.Lock()

    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """Record a gauge metric"""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = {"type": "gauge", "help": help_text, "values": []}

            self.metrics[name]["values"].append(
                {"labels": labels or {}, "value": value, "timestamp": time.time()}
            )

    def counter(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """Record a counter metric"""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = {
                    "type": "counter",
                    "help": help_text,
                    "values": [],
                }

            self.metrics[name]["values"].append(
                {"labels": labels or {}, "value": value, "timestamp": time.time()}
            )

    def histogram(
        self,
        name: str,
        value: float,
        buckets: List[float],
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """Record a histogram observation"""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = {
                    "type": "histogram",
                    "help": help_text,
                    "buckets": buckets,
                    "values": [],
                }

            self.metrics[name]["values"].append(
                {"labels": labels or {}, "value": value, "timestamp": time.time()}
            )

    def exposition_format(self) -> str:
        """Generate Prometheus exposition format output"""
        lines = []

        with self._lock:
            for name, metric in self.metrics.items():
                # Help text
                if metric.get("help"):
                    lines.append(f"# HELP {name} {metric['help']}")

                # Type
                lines.append(f"# TYPE {name} {metric['type']}")

                # Values
                for value_data in metric["values"]:
                    labels_str = ""
                    if value_data["labels"]:
                        labels_parts = [
                            f'{k}="{v}"' for k, v in value_data["labels"].items()
                        ]
                        labels_str = "{" + ",".join(labels_parts) + "}"

                    lines.append(f"{name}{labels_str} {value_data['value']}")

                lines.append("")  # Empty line between metrics

        return "\n".join(lines)

    def clear(self):
        """Clear all metrics"""
        with self._lock:
            self.metrics.clear()


def demo_prometheus_integration():
    """Demonstrate Prometheus integration"""
    print("Initializing Prometheus Metrics Client...")
    client = PrometheusMetricsClient()

    print("\nQuerying InfluxDB metrics...")
    results = client.query("influxdb:query_rate_5m", time=datetime.now(timezone.utc))
    print(f"  Found {len(results)} results")
    for result in results[:3]:
        print(f"    {result.metric}: {result.value}")

    print("\nQuerying TimescaleDB metrics...")
    results = client.query("timescaledb:query_rate_5m", time=datetime.now(timezone.utc))
    print(f"  Found {len(results)} results")

    print("\nQuerying system CPU usage...")
    results = client.query("system:cpu_usage_percent")
    print(f"  Found {len(results)} results")
    for result in results:
        print(
            f"    Instance: {result.metric.get('instance', 'unknown')}, "
            f"CPU: {float(result.value[1]):.2f}%"
        )

    print("\nQuerying composite health score...")
    results = client.query("composite:tsdb_health_score")
    if results:
        score = float(results[0].value[1])
        print(f"  Overall TSDB Health Score: {score:.2f}")

    print("\nExporting custom metrics...")
    exporter = CustomMetricsExporter()

    # Generate some custom metrics
    for i in range(10):
        exporter.gauge(
            "neuralblitz_active_agents",
            value=random.randint(50, 200),
            labels={"environment": "production", "region": "us-east-1"},
            help_text="Number of active NeuralBlitz agents",
        )

        exporter.counter(
            "neuralblitz_tasks_processed_total",
            value=random.randint(1000, 5000),
            labels={"task_type": "inference", "priority": "high"},
            help_text="Total number of tasks processed",
        )

        exporter.histogram(
            "neuralblitz_request_duration_seconds",
            value=random.uniform(0.01, 2.0),
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            labels={"endpoint": "/api/v1/predict"},
            help_text="Request duration in seconds",
        )

    output = exporter.exposition_format()
    print("\n  Generated exposition format (first 20 lines):")
    print("\n".join(output.split("\n")[:20]))

    print("\nPrometheus integration demo completed!")


if __name__ == "__main__":
    demo_prometheus_integration()
