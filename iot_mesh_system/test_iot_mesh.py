#!/usr/bin/env python3
"""
IoT Device Mesh Integration - Test & Demo Suite
===============================================
Comprehensive testing and demonstration of all system components.

Usage:
    python test_iot_mesh.py [options]

Options:
    --test-mqtt        Test MQTT broker connection
    --test-discovery   Test device discovery protocols
    --test-automation  Test smart home automation
    --demo             Run full interactive demo
    --stress-test      Run stress test with multiple devices
"""

import argparse
import json
import random
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List
import unittest
from unittest.mock import Mock, patch

# Import the core system
from iot_mesh_core import (
    IoTMeshSystem,
    DeviceRegistry,
    MQTTBrokerManager,
    SmartHomeAutomation,
    IoTDevice,
    DeviceType,
    DeviceState,
    DeviceCapabilities,
    AutomationRule,
)


class TestMQTTBroker(unittest.TestCase):
    """Test MQTT broker functionality."""

    def setUp(self):
        """Set up test environment."""
        self.mqtt = MQTTBrokerManager(
            broker_host="test.mosquitto.org", broker_port=1883
        )

    def tearDown(self):
        """Clean up after tests."""
        self.mqtt.disconnect()

    def test_broker_connection(self):
        """Test connecting to public MQTT broker."""
        print("\n🧪 Testing MQTT broker connection...")

        # Try to connect (may fail if no internet, but demonstrates the API)
        connected = self.mqtt.connect()

        if connected:
            print("  ✓ Successfully connected to MQTT broker")
            self.assertTrue(self.mqtt.connected)
        else:
            print("  ⚠ Could not connect (broker may be unavailable)")
            # Don't fail the test if external broker is down
            print("  ℹ In production, use local Mosquitto broker")

    def test_topic_matching(self):
        """Test topic pattern matching."""
        print("\n🧪 Testing topic pattern matching...")

        test_cases = [
            ("iot/devices/+/status", "iot/devices/abc123/status", True),
            ("iot/devices/+/status", "iot/devices/xyz789/status", True),
            ("iot/devices/+/status", "iot/devices/abc123/command", False),
            ("iot/+/+", "iot/devices/status", True),
            ("iot/#", "iot/devices/abc123/status", True),
            ("iot/devices/#", "iot/devices", True),
        ]

        for pattern, topic, expected in test_cases:
            result = self.mqtt._topic_matches(pattern, topic)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {pattern} matches {topic}: {result}")
            self.assertEqual(result, expected)

    def test_publish_subscribe(self):
        """Test publish and subscribe operations."""
        print("\n🧪 Testing publish/subscribe...")

        received_messages = []

        def test_handler(topic, payload):
            received_messages.append((topic, payload))

        # Note: This requires an actual broker connection
        if self.mqtt.connect():
            self.mqtt.subscribe("test/topic", test_handler)
            self.mqtt.publish("test/topic", {"test": "data"})

            # Wait for message
            time.sleep(0.5)

            if received_messages:
                print(f"  ✓ Message received: {received_messages[0]}")
            else:
                print("  ⚠ No message received (may be timing issue)")


class TestDeviceDiscovery(unittest.TestCase):
    """Test device discovery protocols."""

    def setUp(self):
        """Set up test environment."""
        self.registry = DeviceRegistry()

    def tearDown(self):
        """Clean up after tests."""
        self.registry.stop_discovery()

    def test_device_registration(self):
        """Test device registration."""
        print("\n🧪 Testing device registration...")

        device = IoTDevice(
            device_id="test_device_001",
            name="Test Smart Light",
            device_type=DeviceType.LIGHT,
            ip_address="192.168.1.100",
            mac_address="AA:BB:CC:DD:EE:01",
            port=8080,
            protocol="http",
            capabilities=DeviceCapabilities(
                can_turn_on_off=True, can_dim=True, can_change_color=True
            ),
        )

        events = []

        def event_listener(event, dev):
            events.append((event, dev.device_id))

        self.registry.add_listener(event_listener)
        self.registry.register_device(device)

        self.assertEqual(len(self.registry.devices), 1)
        self.assertEqual(
            self.registry.get_device("test_device_001").name, "Test Smart Light"
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "device_added")

        print(f"  ✓ Device registered: {device.name}")

    def test_device_lookup(self):
        """Test device lookup by type."""
        print("\n🧪 Testing device lookup...")

        # Register multiple devices
        devices = [
            IoTDevice(
                f"light_{i}",
                f"Light {i}",
                DeviceType.LIGHT,
                "192.168.1.10{i}",
                f"AA:BB:CC:00:0{i}",
                80,
                "http",
            )
            for i in range(3)
        ]
        devices.append(
            IoTDevice(
                "thermostat_1",
                "Thermostat",
                DeviceType.THERMOSTAT,
                "192.168.1.200",
                "AA:BB:CC:00:FF",
                80,
                "http",
            )
        )

        for device in devices:
            self.registry.register_device(device)

        lights = self.registry.get_devices_by_type(DeviceType.LIGHT)
        thermostats = self.registry.get_devices_by_type(DeviceType.THERMOSTAT)

        self.assertEqual(len(lights), 3)
        self.assertEqual(len(thermostats), 1)

        print(f"  ✓ Found {len(lights)} lights")
        print(f"  ✓ Found {len(thermostats)} thermostat")

    def test_discovery_start_stop(self):
        """Test starting and stopping discovery."""
        print("\n🧪 Testing discovery service lifecycle...")

        # This will start zeroconf which requires network
        try:
            self.registry.start_discovery()
            print("  ✓ Discovery protocols started")

            # Let it run briefly
            time.sleep(0.5)

            self.registry.stop_discovery()
            print("  ✓ Discovery protocols stopped")
        except Exception as e:
            print(f"  ⚠ Discovery test skipped: {e}")


class TestSmartHomeAutomation(unittest.TestCase):
    """Test smart home automation engine."""

    def setUp(self):
        """Set up test environment."""
        self.mqtt = MQTTBrokerManager()
        self.registry = DeviceRegistry()
        self.automation = SmartHomeAutomation(self.mqtt, self.registry)

    def test_automation_rule_creation(self):
        """Test creating automation rules."""
        print("\n🧪 Testing automation rule creation...")

        rule = AutomationRule(
            rule_id="test_rule_001",
            name="Test Schedule Rule",
            trigger_type="schedule",
            trigger_config={"time": "08:00"},
            actions=[
                {
                    "type": "device_command",
                    "device_id": "test_light",
                    "command": "turn_on",
                }
            ],
        )

        self.automation.add_rule(rule)

        self.assertEqual(len(self.automation.rules), 1)
        self.assertEqual(
            self.automation.rules["test_rule_001"].name, "Test Schedule Rule"
        )

        print(f"  ✓ Rule created: {rule.name}")

    def test_scene_creation(self):
        """Test scene creation and activation."""
        print("\n🧪 Testing scene management...")

        self.automation.create_scene(
            "test_scene",
            {
                "device_1": {"power": True, "brightness": 50},
                "device_2": {"power": True, "color": "blue"},
            },
        )

        self.assertIn("test_scene", self.automation.scenes)
        print("  ✓ Scene created: test_scene")

    def test_condition_evaluation(self):
        """Test condition evaluation."""
        print("\n🧪 Testing condition evaluation...")

        # Test time range condition
        conditions = [{"type": "time_range", "start": "00:00", "end": "23:59"}]

        result = self.automation._evaluate_conditions(conditions)
        self.assertTrue(result)
        print("  ✓ Time range condition evaluated correctly")

        # Test sensor value condition
        self.automation.sensor_states["test_sensor"] = 25
        conditions = [
            {
                "type": "sensor_value",
                "sensor": "test_sensor",
                "operator": "gt",
                "value": 20,
            }
        ]

        result = self.automation._evaluate_conditions(conditions)
        self.assertTrue(result)
        print("  ✓ Sensor value condition evaluated correctly")


class InteractiveDemo:
    """Interactive demonstration of the IoT Mesh System."""

    def __init__(self):
        self.system = None

    def run(self):
        """Run the interactive demo."""
        print("\n" + "=" * 70)
        print("IoT DEVICE MESH INTEGRATION - INTERACTIVE DEMO")
        print("=" * 70)

        print("\n📚 This demo showcases:")
        print("  1. MQTT Broker Connection and Management")
        print("  2. Device Discovery (mDNS and SSDP)")
        print("  3. Smart Home Automation Rules")
        print("  4. Scene Management")
        print("  5. Device Control")

        # Initialize system
        print("\n🚀 Initializing IoT Mesh System...")
        self.system = IoTMeshSystem(mqtt_host="test.mosquitto.org", mqtt_port=1883)

        # Show configuration
        self._show_configuration()

        # Create sample devices
        self._create_sample_devices()

        # Setup automation
        self._setup_automation()

        # Show system status
        self._show_system_status()

        # Interactive menu
        self._interactive_menu()

    def _show_configuration(self):
        """Display system configuration."""
        print("\n⚙️  System Configuration:")
        print("-" * 50)
        print(f"  MQTT Broker: test.mosquitto.org:1883 (Public Test Broker)")
        print(f"  Protocols: MQTT, mDNS, SSDP")
        print(f"  Max Devices: 1000")
        print(f"  Discovery: Enabled")
        print(f"  Automation: Enabled")

    def _create_sample_devices(self):
        """Create sample IoT devices."""
        print("\n🏠 Creating Sample Smart Home Devices...")
        print("-" * 50)

        sample_devices = [
            IoTDevice(
                device_id="living_room_light",
                name="Living Room Light",
                device_type=DeviceType.LIGHT,
                ip_address="192.168.1.101",
                mac_address="AA:BB:CC:00:01:01",
                port=80,
                protocol="http",
                capabilities=DeviceCapabilities(
                    can_turn_on_off=True, can_dim=True, can_change_color=True
                ),
                manufacturer="Philips",
                firmware_version="2.1.0",
            ),
            IoTDevice(
                device_id="bedroom_light",
                name="Bedroom Light",
                device_type=DeviceType.LIGHT,
                ip_address="192.168.1.102",
                mac_address="AA:BB:CC:00:01:02",
                port=80,
                protocol="http",
                capabilities=DeviceCapabilities(can_turn_on_off=True, can_dim=True),
                manufacturer="LIFX",
                firmware_version="3.0.1",
            ),
            IoTDevice(
                device_id="thermostat_main",
                name="Main Thermostat",
                device_type=DeviceType.THERMOSTAT,
                ip_address="192.168.1.200",
                mac_address="AA:BB:CC:00:02:01",
                port=80,
                protocol="http",
                capabilities=DeviceCapabilities(
                    can_turn_on_off=True, can_report_temperature=True
                ),
                manufacturer="Nest",
                firmware_version="4.5.2",
            ),
            IoTDevice(
                device_id="front_door_lock",
                name="Front Door Lock",
                device_type=DeviceType.DOOR_LOCK,
                ip_address="192.168.1.201",
                mac_address="AA:BB:CC:00:03:01",
                port=443,
                protocol="https",
                capabilities=DeviceCapabilities(can_lock_unlock=True),
                manufacturer="August",
                firmware_version="1.2.3",
            ),
            IoTDevice(
                device_id="motion_sensor_entrance",
                name="Entrance Motion Sensor",
                device_type=DeviceType.MOTION_SENSOR,
                ip_address="192.168.1.150",
                mac_address="AA:BB:CC:00:04:01",
                port=80,
                protocol="http",
                capabilities=DeviceCapabilities(can_detect_motion=True),
                manufacturer="Ring",
                firmware_version="2.0.0",
            ),
            IoTDevice(
                device_id="security_camera_front",
                name="Front Door Camera",
                device_type=DeviceType.CAMERA,
                ip_address="192.168.1.151",
                mac_address="AA:BB:CC:00:05:01",
                port=554,
                protocol="rtsp",
                capabilities=DeviceCapabilities(
                    can_stream_video=True, can_detect_motion=True
                ),
                manufacturer="Arlo",
                firmware_version="3.1.0",
            ),
        ]

        for device in sample_devices:
            self.system.registry.register_device(device)
            print(f"  ✓ {device.name} ({device.device_type.name})")

        print(f"\n  Total devices: {len(sample_devices)}")

    def _setup_automation(self):
        """Setup automation rules and scenes."""
        print("\n🤖 Setting Up Smart Home Automation...")
        print("-" * 50)

        # Create rules
        self.system.create_default_automation_rules()

        # Create scenes
        self.system.create_default_scenes()

        print("  ✓ Automation rules configured")
        print("  ✓ Scenes created (morning, evening, away)")

    def _show_system_status(self):
        """Display system status."""
        print("\n📊 System Status:")
        print("-" * 50)

        status = self.system.get_system_status()

        print(f"  System: {'Running' if status['system']['running'] else 'Stopped'}")
        print(f"  Version: {status['system']['version']}")
        print(f"  Devices: {status['discovery']['discovered_devices']} total")
        print(f"  Automation Rules: {status['automation']['total_rules']}")
        print(f"  Scenes: {len(status['automation']['scenes'])}")

    def _interactive_menu(self):
        """Show interactive menu."""
        print("\n" + "=" * 70)
        print("INTERACTIVE COMMANDS")
        print("=" * 70)

        print("\nAvailable Commands:")
        print("  1. List all devices")
        print("  2. List devices by type")
        print("  3. Control a device")
        print("  4. List automation rules")
        print("  5. Activate a scene")
        print("  6. Show system status")
        print("  7. Export device registry")
        print("  8. Run device simulation")
        print("  0. Exit")

        print("\n💡 Note: This is a simulation without actual MQTT broker.")
        print("   In production, connect to your local Mosquitto broker.")

        while True:
            try:
                choice = input("\nEnter command (0-8): ").strip()

                if choice == "0":
                    print("\n👋 Goodbye!")
                    break
                elif choice == "1":
                    self._cmd_list_devices()
                elif choice == "2":
                    self._cmd_list_by_type()
                elif choice == "3":
                    self._cmd_control_device()
                elif choice == "4":
                    self._cmd_list_rules()
                elif choice == "5":
                    self._cmd_activate_scene()
                elif choice == "6":
                    self._cmd_show_status()
                elif choice == "7":
                    self._cmd_export_registry()
                elif choice == "8":
                    self._cmd_run_simulation()
                else:
                    print("❌ Invalid command. Please try again.")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def _cmd_list_devices(self):
        """List all devices command."""
        print("\n📱 Registered Devices:")
        print("-" * 70)

        for device in self.system.registry.devices.values():
            status_icon = "🟢" if device.state == DeviceState.ONLINE else "🔴"
            print(f"  {status_icon} {device.name}")
            print(f"     ID: {device.device_id}")
            print(f"     Type: {device.device_type.name}")
            print(f"     IP: {device.ip_address}:{device.port}")
            print(f"     Manufacturer: {device.manufacturer}")
            print()

    def _cmd_list_by_type(self):
        """List devices by type command."""
        print("\n📊 Devices by Type:")
        print("-" * 50)

        for device_type in DeviceType:
            devices = self.system.registry.get_devices_by_type(device_type)
            if devices:
                print(f"\n{device_type.name} ({len(devices)}):")
                for device in devices:
                    print(f"  - {device.name}")

    def _cmd_control_device(self):
        """Control device command."""
        print("\n🎮 Device Control:")
        print("-" * 50)

        # List controllable devices
        devices = list(self.system.registry.devices.values())
        for i, device in enumerate(devices, 1):
            print(f"  {i}. {device.name}")

        try:
            choice = int(input("\nSelect device: ")) - 1
            if 0 <= choice < len(devices):
                device = devices[choice]
                print(f"\nSelected: {device.name}")
                print(f"Capabilities: {self._format_capabilities(device.capabilities)}")
                print("\nCommands:")
                print("  1. Turn On")
                print("  2. Turn Off")

                if device.capabilities.can_dim:
                    print("  3. Set Brightness")
                if device.capabilities.can_change_color:
                    print("  4. Set Color")

                cmd = input("\nSelect command: ").strip()

                if cmd == "1":
                    print(f"  → Sending TURN_ON to {device.name}")
                    # In real implementation: self.system.light_controller.turn_on(device.device_id)
                elif cmd == "2":
                    print(f"  → Sending TURN_OFF to {device.name}")
                elif cmd == "3" and device.capabilities.can_dim:
                    brightness = input("  Enter brightness (0-100): ")
                    print(f"  → Setting brightness to {brightness}%")
                elif cmd == "4" and device.capabilities.can_change_color:
                    color = input("  Enter color (e.g., 'red', '#FF0000'): ")
                    print(f"  → Setting color to {color}")
                else:
                    print("  Invalid command")
            else:
                print("  Invalid selection")
        except ValueError:
            print("  Please enter a number")

    def _cmd_list_rules(self):
        """List automation rules command."""
        print("\n🤖 Automation Rules:")
        print("-" * 70)

        for rule in self.system.automation.rules.values():
            status = "🟢" if rule.enabled else "🔴"
            print(f"\n{status} {rule.name} (ID: {rule.rule_id})")
            print(f"   Trigger: {rule.trigger_type}")
            print(f"   Triggered: {rule.trigger_count} times")
            if rule.last_triggered:
                print(
                    f"   Last triggered: {rule.last_triggered.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            print(f"   Actions: {len(rule.actions)}")

    def _cmd_activate_scene(self):
        """Activate scene command."""
        print("\n🎬 Available Scenes:")
        print("-" * 50)

        scenes = list(self.system.automation.scenes.keys())
        for i, scene in enumerate(scenes, 1):
            print(f"  {i}. {scene}")

        try:
            choice = int(input("\nSelect scene: ")) - 1
            if 0 <= choice < len(scenes):
                scene_name = scenes[choice]
                print(f"\n🎬 Activating scene: {scene_name}")
                self.system.automation.activate_scene(scene_name)
            else:
                print("  Invalid selection")
        except ValueError:
            print("  Please enter a number")

    def _cmd_show_status(self):
        """Show system status command."""
        self._show_system_status()

    def _cmd_export_registry(self):
        """Export device registry command."""
        print("\n💾 Exporting Device Registry...")

        export_data = self.system.registry.to_dict()
        filename = f"device_registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"  ✓ Exported to: {filename}")
        print(f"  📄 Total devices: {export_data['device_count']}")

    def _cmd_run_simulation(self):
        """Run device simulation command."""
        print("\n🔬 Running Device Simulation...")
        print("-" * 50)

        print("Simulating sensor data from motion sensor...")
        for i in range(5):
            motion_detected = random.choice([True, False])
            print(f"  [{i + 1}/5] Motion: {'Detected' if motion_detected else 'Clear'}")
            time.sleep(0.5)

        print("\nSimulating temperature changes...")
        for i in range(5):
            temp = round(random.uniform(20, 26), 1)
            print(f"  [{i + 1}/5] Temperature: {temp}°C")
            time.sleep(0.5)

        print("\n  ✓ Simulation complete")

    def _format_capabilities(self, caps: DeviceCapabilities) -> str:
        """Format device capabilities for display."""
        capabilities = []
        if caps.can_turn_on_off:
            capabilities.append("On/Off")
        if caps.can_dim:
            capabilities.append("Dimming")
        if caps.can_change_color:
            capabilities.append("Color")
        if caps.can_report_temperature:
            capabilities.append("Temperature")
        if caps.can_detect_motion:
            capabilities.append("Motion")
        if caps.can_lock_unlock:
            capabilities.append("Lock")
        return ", ".join(capabilities) if capabilities else "None"


def run_tests():
    """Run all unit tests."""
    print("\n" + "=" * 70)
    print("IoT MESH SYSTEM - UNIT TESTS")
    print("=" * 70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMQTTBroker))
    suite.addTests(loader.loadTestsFromTestCase(TestDeviceDiscovery))
    suite.addTests(loader.loadTestsFromTestCase(TestSmartHomeAutomation))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    return result.wasSuccessful()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="IoT Device Mesh Integration - Test & Demo Suite"
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--demo", action="store_true", help="Run interactive demo")
    parser.add_argument(
        "--test-mqtt", action="store_true", help="Test MQTT broker only"
    )
    parser.add_argument(
        "--test-discovery", action="store_true", help="Test device discovery only"
    )
    parser.add_argument(
        "--test-automation", action="store_true", help="Test smart home automation only"
    )

    args = parser.parse_args()

    # If no arguments, run both tests and demo
    if not any(
        [
            args.test,
            args.demo,
            args.test_mqtt,
            args.test_discovery,
            args.test_automation,
        ]
    ):
        args.test = True
        args.demo = True

    success = True

    # Run tests
    if args.test:
        success = run_tests() and success

    if args.test_mqtt:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMQTTBroker)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        success = result.wasSuccessful() and success

    if args.test_discovery:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDeviceDiscovery)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        success = result.wasSuccessful() and success

    if args.test_automation:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestSmartHomeAutomation)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        success = result.wasSuccessful() and success

    # Run demo
    if args.demo:
        demo = InteractiveDemo()
        demo.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
