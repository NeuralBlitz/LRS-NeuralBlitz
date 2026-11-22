#!/usr/bin/env python3
"""Fail CI on unsafe root Compose interpolation and host-port regressions.

Runs docker compose with disposable test-only values; never prints the
interpolated configuration, which includes credential values.
"""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

# Disposable CI values, not credentials for a real service.
DUMMY_ENV = {
    "INFLUXDB_ADMIN_USER": "ci_only_admin",
    "INFLUXDB_ADMIN_PASSWORD": "ci_only_example_password_a",
    "INFLUXDB_USER": "ci_only_user",
    "INFLUXDB_USER_PASSWORD": "ci_only_example_password_b",
    "INFLUXDB_ADMIN_TOKEN": "ci_only_example_token_c",
    "POSTGRES_USER": "ci_only_postgres",
    "POSTGRES_PASSWORD": "ci_only_example_password_d",
    "GRAFANA_ADMIN_USER": "ci_only_grafana",
    "GRAFANA_ADMIN_PASSWORD": "ci_only_example_password_e",
}

# These are the known root monitoring entry points, not a claim that the
# services themselves are authenticated, patched, or production-ready.
LOCAL_PORTS = {
    "influxdb": (8086, 8086),
    "timescaledb": (5432, 5432),
    "prometheus": (9090, 9090),
    "grafana": (3000, 3000),
    "node-exporter": (9100, 9100),
}

# Privileged host metrics must be explicitly enabled.
OPT_IN_PORTS = {"cadvisor": (8080, 8080)}

# Existing security debt: see issue #12. An allowlist must not be construed
# as approval; it merely prevents adding new exceptions silently.
EXISTING_MUTABLE_IMAGES = {
    "timescaledb": "timescale/timescaledb:latest-pg15",
    "prometheus": "prom/prometheus:latest",
    "grafana": "grafana/grafana:latest",
    "node-exporter": "prom/node-exporter:latest",
    "cadvisor": "gcr.io/cadvisor/cadvisor:latest",
}


def load_interpolated_compose(*, include_host_metrics=False):
    env = os.environ.copy()
    env.update(DUMMY_ENV)
    for name in list(env):
        if name.endswith("_BIND_ADDRESS") or name.startswith("COMPOSE_"):
            env.pop(name)
    command = [
        "docker",
        "compose",
        * (["--profile", "host-metrics"] if include_host_metrics else []),
        "--env-file",
        os.devnull,
        "-f",
        "docker-compose.yml",
        "config",
        "--format",
        "json",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker Compose is required for security validation") from exc
    if result.returncode:
        # Never echo stderr/stdout, which could include interpolated secrets.
        raise RuntimeError(
            "Docker Compose could not validate the template with disposable values"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Docker Compose did not return valid JSON") from exc


def check_configuration(config, *, include_host_metrics=False):
    errors = []
    services = config.get("services", {})
    if not isinstance(services, dict):
        return ["No services found in Compose configuration"]

    expected_ports = dict(LOCAL_PORTS)
    if include_host_metrics:
        expected_ports.update(OPT_IN_PORTS)

    for name, entry in services.items():
        if not isinstance(entry, dict):
            errors.append(f"{name}: invalid service configuration")
            continue

        ports = entry.get("ports", [])
        expected = expected_ports.get(name)
        if expected is None:
            errors.append(f"{name}: unexpected service enabled in this profile")
            if ports:
                errors.append(f"{name}: unexpected published host port(s)")
        else:
            if len(ports) != 1:
                errors.append(f"{name}: expected exactly one published localhost port")
            for port in ports:
                if not isinstance(port, dict):
                    errors.append(f"{name}: expected normalized port mapping")
                    continue
                if port.get("host_ip") != "127.0.0.1":
                    errors.append(f"{name}: published port is not bound to localhost")
                try:
                    actual = (int(port.get("published")), int(port.get("target")))
                except (TypeError, ValueError):
                    errors.append(f"{name}: invalid published port mapping")
                else:
                    if actual != expected:
                        errors.append(f"{name}: unexpected published port mapping")

        if entry.get("privileged", False) and not (include_host_metrics and name == "cadvisor"):
            errors.append(f"{name}: new privileged container is prohibited")

        image = entry.get("image", "")
        if ":latest" in image and EXISTING_MUTABLE_IMAGES.get(name) != image:
            errors.append(f"{name}: new or modified mutable latest image reference")

    for name in expected_ports:
        if name not in services:
            errors.append(f"{name}: expected monitoring service is missing")

    credential_fields = {
        "influxdb": {
            "INFLUXDB_ADMIN_USER",
            "INFLUXDB_ADMIN_PASSWORD",
            "INFLUXDB_USER",
            "INFLUXDB_USER_PASSWORD",
            "INFLUXDB_ADMIN_TOKEN",
        },
        "timescaledb": {"POSTGRES_USER", "POSTGRES_PASSWORD"},
        "grafana": {"GF_SECURITY_ADMIN_USER", "GF_SECURITY_ADMIN_PASSWORD"},
    }
    field_env = {
        "GF_SECURITY_ADMIN_USER": "GRAFANA_ADMIN_USER",
        "GF_SECURITY_ADMIN_PASSWORD": "GRAFANA_ADMIN_PASSWORD",
    }
    for service, fields in credential_fields.items():
        entry = services.get(service, {})
        actual_env = entry.get("environment", {}) if isinstance(entry, dict) else {}
        if not isinstance(actual_env, dict):
            errors.append(f"{service}: expected structured service environment")
            continue
        for field in fields:
            variable = field_env.get(field, field)
            if actual_env.get(field) != DUMMY_ENV[variable]:
                errors.append(
                    f"{service}: {field} does not use the required injected value"
                )
    return errors


def main():
    try:
        config = load_interpolated_compose()
        errors = check_configuration(config)
        opted_in = load_interpolated_compose(include_host_metrics=True)
        errors.extend(
            "host-metrics: " + issue
            for issue in check_configuration(opted_in, include_host_metrics=True)
        )
    except RuntimeError as exc:
        print(f"Compose security validation failed: {exc}", file=sys.stderr)
        return 1

    for problem in errors:
        print(f"FAIL: {problem}", file=sys.stderr)
    if errors:
        return 1

    print(
        "PASS: root Compose uses injected dummy credentials and localhost-only "
        "published ports; privileged cAdvisor is off by default and opt-in only."
    )
    print(
        "KNOWN DEBT: opted-in cAdvisor privilege and existing mutable images remain "
        "unresolved; see issue #12."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
