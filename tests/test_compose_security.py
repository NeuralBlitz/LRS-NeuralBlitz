"""Mutation-focused tests of the root Compose security policy."""

import copy
import importlib.util
from pathlib import Path
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_compose_security.py"
spec = importlib.util.spec_from_file_location("check_compose_security", CHECKER)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def valid_configuration(include_host_metrics=False):
    services = {}
    expected = dict(policy.LOCAL_PORTS)
    if include_host_metrics:
        expected.update(policy.OPT_IN_PORTS)
    for name, (published, target) in expected.items():
        services[name] = {
            "ports": [{
                "host_ip": "127.0.0.1",
                "published": str(published),
                "target": target,
            }],
            "environment": {},
            "image": policy.EXISTING_MUTABLE_IMAGES.get(name, "influxdb:2.7"),
        }

    services["influxdb"]["environment"] = {
        field: policy.DUMMY_ENV[field]
        for field in (
            "INFLUXDB_ADMIN_USER",
            "INFLUXDB_ADMIN_PASSWORD",
            "INFLUXDB_USER",
            "INFLUXDB_USER_PASSWORD",
            "INFLUXDB_ADMIN_TOKEN",
        )
    }
    services["timescaledb"]["environment"] = {
        field: policy.DUMMY_ENV[field] for field in ("POSTGRES_USER", "POSTGRES_PASSWORD")
    }
    services["grafana"]["environment"] = {
        "GF_SECURITY_ADMIN_USER": policy.DUMMY_ENV["GRAFANA_ADMIN_USER"],
        "GF_SECURITY_ADMIN_PASSWORD": policy.DUMMY_ENV["GRAFANA_ADMIN_PASSWORD"],
    }
    if include_host_metrics:
        services["cadvisor"]["privileged"] = True  # Explicit opt-in exception only.
    return {"services": services}


class ComposePolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = valid_configuration()

    def assert_rejected(self, text, *, include_host_metrics=False):
        failures = policy.check_configuration(
            self.config, include_host_metrics=include_host_metrics
        )
        self.assertTrue(
            any(text in failure for failure in failures), failures
        )

    def test_existing_known_baseline_is_accepted(self):
        self.assertEqual(policy.check_configuration(self.config), [])

    def test_opt_in_host_metrics_maintains_known_security_debt(self):
        self.config = valid_configuration(include_host_metrics=True)
        self.assertEqual(
            policy.check_configuration(self.config, include_host_metrics=True), []
        )
        self.assertTrue(self.config["services"]["cadvisor"]["privileged"])

    def test_privileged_cadvisor_in_default_profile_is_rejected(self):
        self.config = valid_configuration(include_host_metrics=True)
        self.assert_rejected("unexpected service enabled in this profile")
        self.assert_rejected("new privileged container")

    def test_profiled_cadvisor_must_be_present_when_opted_in(self):
        self.config = valid_configuration(include_host_metrics=True)
        del self.config["services"]["cadvisor"]
        self.assert_rejected(
            "expected monitoring service is missing", include_host_metrics=True
        )

    def test_profiled_cadvisor_cannot_bind_wildcard_address(self):
        self.config = valid_configuration(include_host_metrics=True)
        self.config["services"]["cadvisor"]["ports"][0]["host_ip"] = "0.0.0.0"
        self.assert_rejected("not bound to localhost", include_host_metrics=True)

    def test_unexpected_unpublished_default_service_is_rejected(self):
        self.config["services"]["rogue"] = {"image": "busybox:1", "ports": []}
        self.assert_rejected("unexpected service enabled in this profile")

    def test_wildcard_host_binding_is_rejected(self):
        self.config["services"]["grafana"]["ports"][0]["host_ip"] = "0.0.0.0"
        self.assert_rejected("not bound to localhost")

    def test_changed_host_port_is_rejected(self):
        self.config["services"]["grafana"]["ports"][0]["published"] = "4000"
        self.assert_rejected("unexpected published port mapping")

    def test_new_exposed_service_is_rejected(self):
        self.config["services"]["rogue"] = {
            "ports": [{"host_ip": "0.0.0.0", "published": "1234", "target": 1234}]
        }
        self.assert_rejected("unexpected published host port")

    def test_literal_credential_is_rejected(self):
        self.config["services"]["timescaledb"]["environment"]["POSTGRES_PASSWORD"] = "literal"
        self.assert_rejected("does not use the required injected value")

    def test_new_privileged_container_is_rejected(self):
        self.config["services"]["grafana"]["privileged"] = True
        self.assert_rejected("new privileged container")

    def test_new_latest_image_is_rejected(self):
        self.config["services"]["influxdb"]["image"] = "influxdb:latest"
        self.assert_rejected("mutable latest image")

    def test_service_disappearance_is_rejected(self):
        del self.config["services"]["grafana"]
        self.assert_rejected("expected monitoring service is missing")


if __name__ == "__main__":
    unittest.main()
