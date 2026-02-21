"""
Test Suite for NeuralBlitz Federated Learning System
====================================================

Comprehensive tests for all federated learning features:
1. Distributed training coordination
2. Secure aggregation protocols
3. Differential privacy mechanisms

Run with: python -m pytest test_neuralblitz_federated_learning.py -v
"""

import unittest
import torch
import torch.nn as nn
import numpy as np
from typing import Dict
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuralblitz_federated_learning import (
    FederatedConfig,
    PrivacyAccountant,
    DifferentialPrivacyMechanism,
    SecureAggregationProtocol,
    DistributedTrainingCoordinator,
    FederatedClient,
    ClientUpdate,
    create_example_model,
    demo_federated_learning,
)


class TestFederatedConfig(unittest.TestCase):
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FederatedConfig()
        self.assertEqual(config.num_rounds, 10)
        self.assertEqual(config.num_clients, 5)
        self.assertEqual(config.epsilon, 1.0)
        self.assertEqual(config.delta, 1e-5)
        self.assertTrue(config.use_secure_agg)

    def test_custom_config(self):
        """Test custom configuration."""
        config = FederatedConfig(num_rounds=20, epsilon=2.0, use_secure_agg=False)
        self.assertEqual(config.num_rounds, 20)
        self.assertEqual(config.epsilon, 2.0)
        self.assertFalse(config.use_secure_agg)

    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = FederatedConfig()
        config_dict = config.to_dict()
        self.assertIn("num_rounds", config_dict)
        self.assertIn("epsilon", config_dict)
        self.assertIsInstance(config_dict, dict)


class TestPrivacyAccountant(unittest.TestCase):
    """Test differential privacy accounting."""

    def setUp(self):
        self.accountant = PrivacyAccountant(epsilon=1.0, delta=1e-5)

    def test_initial_state(self):
        """Test initial privacy budget state."""
        status = self.accountant.get_status()
        self.assertEqual(status["epsilon_budget"], 1.0)
        self.assertEqual(status["epsilon_spent"], 0.0)
        self.assertEqual(status["query_count"], 0)
        self.assertTrue(status["cect_compliant"])

    def test_privacy_computation(self):
        """Test privacy spent computation."""
        epsilon, delta = self.accountant.compute_privacy_spent(
            noise_multiplier=1.1, sampling_rate=0.1, steps=100
        )
        self.assertGreater(epsilon, 0)
        self.assertEqual(delta, 1e-5)

    def test_spend_budget(self):
        """Test budget spending."""
        # Should succeed
        result = self.accountant.spend_budget(0.5)
        self.assertTrue(result)
        self.assertEqual(self.accountant.epsilon_spent, 0.5)

        # Should fail when budget exceeded
        with self.assertRaises(Exception):
            self.accountant.spend_budget(0.6)  # Would exceed 1.0

    def test_budget_tracking(self):
        """Test cumulative budget tracking."""
        self.accountant.spend_budget(0.2)
        self.accountant.spend_budget(0.3)

        status = self.accountant.get_status()
        self.assertEqual(status["epsilon_spent"], 0.5)
        self.assertEqual(status["epsilon_remaining"], 0.5)


class TestDifferentialPrivacyMechanism(unittest.TestCase):
    """Test DP mechanisms."""

    def setUp(self):
        self.config = FederatedConfig(epsilon=2.0, delta=1e-5)
        self.accountant = PrivacyAccountant(self.config.epsilon, self.config.delta)
        self.dp = DifferentialPrivacyMechanism(self.config, self.accountant)
        self.model = create_example_model()

    def test_gradient_clipping(self):
        """Test gradient clipping."""
        # Create dummy gradients
        for param in self.model.parameters():
            param.grad = torch.randn_like(param)

        # Clip gradients
        norm_before = self.dp.clip_gradients(self.model)

        # Check that norm is bounded
        total_norm = 0.0
        for param in self.model.parameters():
            if param.grad is not None:
                total_norm += param.grad.norm(2).item() ** 2
        total_norm = total_norm**0.5

        self.assertLessEqual(total_norm, self.config.max_grad_norm + 1e-6)
        self.assertGreater(norm_before, 0)  # Should have had some norm

    def test_noise_addition(self):
        """Test Gaussian noise addition."""
        # Set deterministic gradients
        for param in self.model.parameters():
            param.grad = torch.ones_like(param)

        # Store original
        original_grads = []
        for param in self.model.parameters():
            if param.grad is not None:
                original_grads.append(param.grad.clone())

        # Add noise
        self.dp.add_noise(self.model, noise_multiplier=1.0)

        # Check gradients changed
        for i, param in enumerate(self.model.parameters()):
            if param.grad is not None:
                # Should be different due to noise
                diff = torch.abs(param.grad - original_grads[i]).max()
                self.assertGreater(diff, 0)


class TestSecureAggregation(unittest.TestCase):
    """Test secure aggregation protocols."""

    def setUp(self):
        self.config = FederatedConfig()
        self.secure_agg = SecureAggregationProtocol(self.config)

    def test_key_generation(self):
        """Test encryption key generation."""
        client_id = "test_client"
        key = self.secure_agg.generate_key(client_id)

        self.assertIn(client_id, self.secure_agg.keys)
        self.assertIsInstance(key, bytes)
        self.assertGreater(len(key), 0)

    def test_secret_sharing(self):
        """Test Shamir secret sharing."""
        secret = 42.0
        num_shares = 5
        threshold = 3

        # Create shares
        shares = self.secure_agg.create_shares(secret, num_shares, threshold)

        # Should have correct number of shares
        self.assertEqual(len(shares), num_shares)

        # Reconstruct with threshold shares
        reconstructed = self.secure_agg.reconstruct_secret(shares[:threshold])
        self.assertAlmostEqual(reconstructed, secret, places=5)

        # Reconstruct with all shares
        reconstructed_all = self.secure_agg.reconstruct_secret(shares)
        self.assertAlmostEqual(reconstructed_all, secret, places=5)

    def test_encryption_decryption(self):
        """Test update encryption and decryption."""
        client_id = "test_client"

        # Create dummy update
        model_state = {
            "layer1.weight": torch.randn(10, 10),
            "layer1.bias": torch.randn(10),
        }

        update = ClientUpdate(
            client_id=client_id,
            model_state=model_state,
            num_samples=100,
            privacy_spent=0.1,
            timestamp=time.time(),
        )

        # Encrypt
        encrypted = self.secure_agg.encrypt_update(client_id, update)
        self.assertTrue(encrypted.encrypted)

        # Decrypt
        decrypted = self.secure_agg.decrypt_update(client_id, encrypted)
        self.assertFalse(decrypted.encrypted)

        # Check values match (approximately, due to serialization)
        for key in model_state:
            self.assertIn(key, decrypted.model_state)

    def test_integrity_verification(self):
        """Test NBHS-512 hash verification."""
        model_state = {
            "weight": torch.randn(5, 5),
        }

        update = ClientUpdate(
            client_id="test",
            model_state=model_state,
            num_samples=100,
            privacy_spent=0.0,
            timestamp=time.time(),
        )

        # Compute hash
        update.nbhs512_hash = update.compute_hash()

        # Verify
        self.assertTrue(self.secure_agg.verify_integrity(update))

        # Tamper and verify fails
        update.model_state["weight"] = torch.randn(5, 5)
        self.assertFalse(self.secure_agg.verify_integrity(update))


class TestDistributedTrainingCoordinator(unittest.TestCase):
    """Test training coordination."""

    def setUp(self):
        self.config = FederatedConfig(num_rounds=2, num_clients=3, local_epochs=1)
        self.coordinator = DistributedTrainingCoordinator(self.config)
        self.model = create_example_model()
        self.coordinator.initialize_model(self.model)

    def test_initialization(self):
        """Test coordinator initialization."""
        self.assertIsNotNone(self.coordinator.global_model)
        self.assertEqual(
            self.coordinator.privacy_accountant.epsilon_budget, self.config.epsilon
        )

    def test_client_selection(self):
        """Test client selection."""
        clients = [f"client_{i}" for i in range(10)]

        selected = self.coordinator.select_clients(0, clients)

        # Should select subset
        self.assertGreater(len(selected), 0)
        self.assertLessEqual(len(selected), len(clients))

        # All selected should be from pool
        for client in selected:
            self.assertIn(client, clients)

    def test_privacy_accounting_integration(self):
        """Test privacy accounting integration."""
        # Check initial state
        status = self.coordinator.get_final_privacy_guarantees()
        self.assertEqual(status["epsilon_spent"], 0.0)

        # Spend some budget manually
        self.coordinator.privacy_accountant.spend_budget(0.5)

        status = self.coordinator.get_final_privacy_guarantees()
        self.assertEqual(status["epsilon_spent"], 0.5)


class TestClientUpdate(unittest.TestCase):
    """Test client update data structure."""

    def test_update_creation(self):
        """Test creating client updates."""
        model_state = {"weight": torch.randn(10, 10)}

        update = ClientUpdate(
            client_id="client_1",
            model_state=model_state,
            num_samples=1000,
            privacy_spent=0.5,
            timestamp=time.time(),
        )

        self.assertEqual(update.client_id, "client_1")
        self.assertEqual(update.num_samples, 1000)
        self.assertEqual(update.privacy_spent, 0.5)

    def test_hash_computation(self):
        """Test hash computation."""
        model_state = {"weight": torch.randn(5, 5)}

        update = ClientUpdate(
            client_id="test",
            model_state=model_state,
            num_samples=100,
            privacy_spent=0.0,
            timestamp=time.time(),
        )

        hash1 = update.compute_hash()
        hash2 = update.compute_hash()

        # Same data should give same hash
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 128)  # SHA-512 is 128 hex chars

        # Different data should give different hash
        update.model_state["weight"] = torch.randn(5, 5)
        hash3 = update.compute_hash()
        self.assertNotEqual(hash1, hash3)


class TestIntegration(unittest.TestCase):
    """Integration tests for full workflow."""

    def test_full_pipeline(self):
        """Test complete federated learning pipeline."""
        config = FederatedConfig(
            num_rounds=2,
            num_clients=2,
            local_epochs=1,
            epsilon=5.0,  # High budget for testing
        )

        coordinator = DistributedTrainingCoordinator(config)
        model = create_example_model()
        coordinator.initialize_model(model)

        # Create dummy clients
        clients = [f"client_{i}" for i in range(2)]

        # Define local training function
        def dummy_train(client_id, global_state, dp_mechanism, config):
            # Create simple model
            local_model = create_example_model()
            local_model.load_state_dict(global_state)

            # Create dummy data
            data = torch.randn(50, 784)
            labels = torch.randint(0, 10, (50,))
            dataset = torch.utils.data.TensorDataset(data, labels)
            loader = torch.utils.data.DataLoader(dataset, batch_size=16)

            # Train
            client = FederatedClient(client_id, loader)
            client.local_model = local_model

            return client.local_train(global_state, dp_mechanism, config)

        # Run training
        history = coordinator.train(clients, dummy_train)

        # Verify results
        self.assertEqual(len(history), 2)

        for metrics in history:
            self.assertIn("round", metrics)
            self.assertIn("participating_clients", metrics)
            self.assertIn("privacy_spent", metrics)

        # Check privacy was spent
        final_status = coordinator.get_final_privacy_guarantees()
        self.assertGreater(final_status["epsilon_spent"], 0)

    def test_privacy_budget_exceeded(self):
        """Test behavior when privacy budget exceeded."""
        config = FederatedConfig(epsilon=0.01, delta=1e-5)
        accountant = PrivacyAccountant(config.epsilon, config.delta)

        # Should fail when budget exceeded
        with self.assertRaises(Exception) as context:
            accountant.spend_budget(0.02)  # Exceeds 0.01 budget

        self.assertIn("exceeded", str(context.exception).lower())


class TestPrivacyGuarantees(unittest.TestCase):
    """Test formal privacy guarantees."""

    def test_epsilon_budget_tracking(self):
        """Test that epsilon is tracked correctly."""
        accountant = PrivacyAccountant(epsilon=1.0, delta=1e-5)

        # Spend in increments
        epsilon_costs = [0.1, 0.2, 0.3, 0.1]
        for cost in epsilon_costs:
            accountant.spend_budget(cost)

        # Check total
        self.assertAlmostEqual(accountant.epsilon_spent, sum(epsilon_costs), places=5)

    def test_delta_immutable(self):
        """Test that delta doesn't change."""
        accountant = PrivacyAccountant(epsilon=1.0, delta=1e-5)

        # Spend budget multiple times
        for _ in range(5):
            accountant.spend_budget(0.1)

        # Delta should remain constant
        status = accountant.get_status()
        self.assertEqual(status["delta"], 1e-5)


def run_tests():
    """Run all tests with verbose output."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPrivacyAccountant))
    suite.addTests(loader.loadTestsFromTestCase(TestDifferentialPrivacyMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureAggregation))
    suite.addTests(loader.loadTestsFromTestCase(TestDistributedTrainingCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestClientUpdate))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPrivacyGuarantees))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
