"""Non-network checks for the stage-cluster arithmetic simulation.

The script models hypothetical totals and must not claim to have provisioned
real cloud workers or produced cryptographic deployment attestation.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment_summary.py"


class SimulationTruthTests(unittest.TestCase):
    def test_arithmetic_demo_does_not_claim_actual_agent_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SOURCE)], cwd=tmp,
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SIMULATION COMPLETE - NO INFRASTRUCTURE DEPLOYED", result.stdout)
            self.assertIn("hypothetical agents counted", result.stdout)
            self.assertIn("Actual provisioning throughput: not measured", result.stdout)
            self.assertNotIn("Total Agents Deployed:", result.stdout)
            self.assertNotIn("Deployment Rate:", result.stdout)
            self.assertFalse((Path(tmp) / "deployment_goldendag.json").exists())

            path = Path(tmp) / "simulated_stage_clusters_goldendag.json"
            self.assertTrue(path.is_file())
            simulated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(simulated), 10)
            for item in simulated:
                self.assertIs(item["simulation_only"], True)
                self.assertIsNone(item["attestation"])
                self.assertIn("synthetic-offset", item["timestamp_origin"])

    def test_report_metadata_is_not_remote_proof(self):
        src = SOURCE.read_text(encoding="utf-8")
        self.assertIn("not observed workers", src)
        self.assertNotIn('dag_filename = "deployment_goldendag.json"', src)


if __name__ == "__main__":
    unittest.main()
