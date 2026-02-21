#!/usr/bin/env python3
"""
InfluxDB Telemetry Client
Handles writing and querying telemetry data from InfluxDB v2.x
"""

import os
import time
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.domain.write_precision import WritePrecision


@dataclass
class TelemetryMetric:
    """Represents a single telemetry metric"""

    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, Any]
    timestamp: Optional[datetime] = None


class InfluxDBTelemetryClient:
    """Client for interacting with InfluxDB for telemetry storage"""

    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = "telemetry-token-xyz",
        org: str = "neuralblitz",
        bucket: str = "system_metrics",
    ):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket

        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def write_metric(self, metric: TelemetryMetric) -> bool:
        """Write a single metric to InfluxDB"""
        try:
            point = Point(metric.measurement)

            # Add tags
            for key, value in metric.tags.items():
                point = point.tag(key, value)

            # Add fields
            for key, value in metric.fields.items():
                if isinstance(value, int):
                    point = point.field(key, float(value))
                elif isinstance(value, float):
                    point = point.field(key, value)
                elif isinstance(value, bool):
                    point = point.field(key, value)
                else:
                    point = point.field(key, str(value))

            # Set timestamp
            if metric.timestamp:
                point = point.time(metric.timestamp, WritePrecision.NS)
            else:
                point = point.time(datetime.now(timezone.utc), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, record=point)
            return True

        except Exception as e:
            print(f"Error writing metric: {e}")
            return False

    def write_batch(self, metrics: List[TelemetryMetric]) -> int:
        """Write multiple metrics in batch"""
        success_count = 0
        for metric in metrics:
            if self.write_metric(metric):
                success_count += 1
        return success_count

    def query_metrics(
        self,
        measurement: str,
        start_time: str = "-1h",
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query metrics from InfluxDB using Flux"""
        try:
            filter_str = ""
            if filters:
                for key, value in filters.items():
                    filter_str += f' |> filter(fn: (r) => r["{key}"] == "{value}")'

            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {start_time})
                |> filter(fn: (r) => r._measurement == "{measurement}"){filter_str}
                |> sort(columns: ["_time"], desc: true)
            '''

            result = self.query_api.query(query=query, org=self.org)

            metrics = []
            for table in result:
                for record in table.records:
                    metrics.append(
                        {
                            "time": record.get_time(),
                            "measurement": record.get_measurement(),
                            "field": record.get_field(),
                            "value": record.get_value(),
                            "tags": {
                                k: v
                                for k, v in record.values.items()
                                if k
                                not in [
                                    "_time",
                                    "_measurement",
                                    "_field",
                                    "_value",
                                    "result",
                                    "table",
                                ]
                            },
                        }
                    )

            return metrics

        except Exception as e:
            print(f"Error querying metrics: {e}")
            return []

    def get_system_metrics(self) -> TelemetryMetric:
        """Generate system telemetry metrics"""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return TelemetryMetric(
            measurement="system_telemetry",
            tags={
                "host": "neuralblitz-server-01",
                "region": "us-east-1",
                "environment": "production",
            },
            fields={
                "cpu_percent": cpu_percent,
                "memory_used_percent": memory.percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_used_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "load_avg_1m": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0,
            },
            timestamp=datetime.now(timezone.utc),
        )

    def get_application_metrics(self) -> TelemetryMetric:
        """Generate application-level telemetry"""
        return TelemetryMetric(
            measurement="application_telemetry",
            tags={
                "service": "neuralblitz-core",
                "version": "v20.0",
                "instance": "instance-001",
            },
            fields={
                "requests_per_second": random.uniform(100, 500),
                "response_time_ms": random.uniform(10, 100),
                "error_rate": random.uniform(0.001, 0.01),
                "active_connections": random.randint(50, 200),
                "queue_depth": random.randint(0, 50),
            },
            timestamp=datetime.now(timezone.utc),
        )

    def close(self):
        """Close the InfluxDB client"""
        self.write_api.close()
        self.client.close()


def setup_influxdb_retention_policies():
    """Setup retention policies for different metric types"""
    client = InfluxDBClient(
        url="http://localhost:8086", token="telemetry-token-xyz", org="neuralblitz"
    )

    buckets_api = client.buckets_api()

    # Create bucket for high-frequency metrics (7 day retention)
    try:
        buckets_api.create_bucket(
            bucket_name="high_freq_metrics",
            org_id="neuralblitz",
            retention_rules=[
                {
                    "type": "expire",
                    "everySeconds": 604800,  # 7 days
                }
            ],
        )
        print("Created bucket: high_freq_metrics")
    except Exception as e:
        print(f"Bucket high_freq_metrics may already exist: {e}")

    # Create bucket for aggregated metrics (90 day retention)
    try:
        buckets_api.create_bucket(
            bucket_name="aggregated_metrics",
            org_id="neuralblitz",
            retention_rules=[
                {
                    "type": "expire",
                    "everySeconds": 7776000,  # 90 days
                }
            ],
        )
        print("Created bucket: aggregated_metrics")
    except Exception as e:
        print(f"Bucket aggregated_metrics may already exist: {e}")

    client.close()


def demo_telemetry_collection():
    """Demonstrate telemetry collection and storage"""
    print("Initializing InfluxDB Telemetry Client...")
    client = InfluxDBTelemetryClient()

    print("\nGenerating and writing system telemetry...")
    for i in range(10):
        metric = client.get_system_metrics()
        success = client.write_metric(metric)
        print(f"  Metric {i + 1}/10: {'✓' if success else '✗'}")
        time.sleep(1)

    print("\nGenerating and writing application telemetry...")
    for i in range(5):
        metric = client.get_application_metrics()
        success = client.write_metric(metric)
        print(f"  Metric {i + 1}/5: {'✓' if success else '✗'}")
        time.sleep(0.5)

    print("\nQuerying recent metrics...")
    system_metrics = client.query_metrics(
        measurement="system_telemetry", start_time="-5m"
    )

    print(f"Found {len(system_metrics)} system telemetry records")
    if system_metrics:
        print("\nLatest metrics:")
        for metric in system_metrics[:3]:
            print(
                f"  Time: {metric['time']}, Field: {metric['field']}, Value: {metric['value']}"
            )

    client.close()
    print("\nInfluxDB telemetry demo completed!")


if __name__ == "__main__":
    # First, setup retention policies
    setup_influxdb_retention_policies()

    # Then run the demo
    demo_telemetry_collection()
