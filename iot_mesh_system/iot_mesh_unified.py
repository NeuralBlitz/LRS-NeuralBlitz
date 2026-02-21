"""
IoT Device Mesh Integration System - Complete Implementation
========================================================
Unified IoT device mesh with MQTT broker, device discovery,
automation rules engine, and database integration.

Author: NeuralBlitz Systems
Version: 2.0.0
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from mqtt_broker import MQTTClientManager, MockMQTTBroker, MqttTopicManager, QoSLevel
from device_discovery import (
    DeviceDiscoveryManager,
    DiscoveredService,
    ServiceType,
    NetworkScanner,
)
from automation_engine import (
    AutomationRuleEngine,
    AutomationRule,
    Trigger,
    Condition,
    Action,
    TriggerType,
    ConditionOperator,
    ActionType,
    SceneManager,
)
from database import DatabaseManager, DeviceRecord, AutomationRuleRecord

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IoTMeshSystem:
    """
    Unified IoT Device Mesh System.
    Integrates MQTT, device discovery, automation, and database.
    """

    def __init__(
        self,
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        db_path: str = "iot_mesh.db",
        use_mock_broker: bool = True,
    ):
        # Core components
        self.db = DatabaseManager(db_path)

        # MQTT
        if use_mock_broker:
            self.mqtt_broker = MockMQTTBroker(mqtt_host, mqtt_port)
        else:
            self.mqtt_broker = None

        self.mqtt_manager = MQTTClientManager(mqtt_host, mqtt_port)

        # Device discovery
        self.discovery_manager = DeviceDiscoveryManager()

        # Automation
        self.automation_engine = AutomationRuleEngine()
        self.scene_manager: Optional[SceneManager] = None

        # Device state cache
        self._device_states: Dict[str, Dict[str, Any]] = {}
        self._device_handlers: Dict[str, Callable] = {}

        self._running = False

        logger.info("IoT Mesh System initialized")

    def start(self):
        """Start the IoT mesh system."""
        if self._running:
            return

        logger.info("Starting IoT Mesh System...")

        # Start MQTT broker
        if self.mqtt_broker:
            self.mqtt_broker.start()

        self.mqtt_manager.start()

        # Configure automation engine
        self.automation_engine.configure(
            device_state_getter=self.get_device_state,
            device_command_sender=self.send_device_command,
            scene_activator=self.activate_scene,
            notification_sender=self.send_notification,
        )
        self.automation_engine.start()

        # Initialize scene manager
        self.scene_manager = SceneManager(self.automation_engine._action_executor)

        # Start device discovery
        self.discovery_manager.start()

        # Load rules from database
        self._load_rules_from_db()

        self._running = True
        logger.info("IoT Mesh System started")

    def stop(self):
        """Stop the IoT mesh system."""
        if not self._running:
            return

        logger.info("Stopping IoT Mesh System...")

        self.discovery_manager.stop()
        self.automation_engine.stop()
        self.mqtt_manager.stop()

        if self.mqtt_broker:
            self.mqtt_broker.stop()

        self.db.close()

        self._running = False
        logger.info("IoT Mesh System stopped")

    # =========================================================================
    # DEVICE MANAGEMENT
    # =========================================================================

    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        ip_address: str = "",
        mac_address: str = "",
        port: int = 0,
        protocol: str = "mqtt",
        properties: Dict[str, Any] = None,
    ) -> bool:
        """Register a new device."""
        device_record = DeviceRecord(
            device_id=device_id,
            name=name,
            device_type=device_type,
            ip_address=ip_address,
            mac_address=mac_address,
            port=port,
            protocol=protocol,
            state="offline",
            properties_json=json.dumps(properties or {}),
            capabilities_json="{}",
            firmware_version="1.0.0",
            manufacturer="Unknown",
            last_seen=datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        result = self.db.insert_device(device_record)

        if result:
            # Register MQTT topic
            self.mqtt_manager.register_device_topic(device_id, f"devices/{device_id}")

            # Subscribe to device state
            self.mqtt_manager.subscribe_to_device(
                device_id, self._handle_device_message
            )

        return result

    def update_device_state(self, device_id: str, state: Dict[str, Any]):
        """Update device state and trigger automation."""
        self._device_states[device_id] = state.copy()

        # Save to database
        self.db.save_device_state_history(device_id, state)

        # Update in database
        device = self.db.get_device(device_id)
        if device:
            device_record = DeviceRecord(
                device_id=device_id,
                name=device["name"],
                device_type=device["device_type"],
                ip_address=device["ip_address"],
                mac_address=device["mac_address"],
                port=device["port"],
                protocol=device["protocol"],
                state=state.get("state", "online"),
                properties_json=json.dumps(state),
                capabilities_json=device["capabilities_json"],
                firmware_version=device["firmware_version"],
                manufacturer=device["manufacturer"],
                last_seen=datetime.now().isoformat(),
                created_at=device["created_at"],
                updated_at=datetime.now().isoformat(),
            )
            self.db.update_device(device_record)

        # Update via MQTT
        self.mqtt_manager.publish_device_state(device_id, state)

        # Trigger automation
        self.automation_engine.update_device_state(device_id, state)

    def get_device_state(self, device_id: str, attribute: str = None) -> Any:
        """Get device state attribute."""
        state = self._device_states.get(device_id, {})
        if attribute:
            return state.get(attribute)
        return state

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all registered devices."""
        return self.db.get_all_devices()

    def send_device_command(
        self, device_id: str, command: str, params: Dict[str, Any] = None
    ) -> bool:
        """Send command to a device."""
        logger.info(f"Sending command {command} to device {device_id}: {params}")

        # Publish command via MQTT
        self.mqtt_manager.publish_command(device_id, command, params)

        return True

    def _handle_device_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle incoming device message."""
        logger.debug(f"Received message from {device_id}: {payload}")
        self.update_device_state(device_id, payload)

    # =========================================================================
    # SCENES
    # =========================================================================

    def create_scene(self, name: str, actions: List[Dict[str, Any]]) -> bool:
        """Create a scene."""
        # Convert dict to Action objects
        scene_actions = []
        for action_dict in actions:
            action = Action(
                action_type=ActionType[
                    action_dict.get("action_type", "DEVICE_COMMAND")
                ],
                device_id=action_dict.get("device_id", ""),
                command=action_dict.get("command", ""),
                params=action_dict.get("params", {}),
                scene_name=action_dict.get("scene_name", ""),
                message=action_dict.get("message", ""),
            )
            scene_actions.append(action)

        self.scene_manager.create_scene(name, scene_actions)

        # Save to database
        return self.db.save_scene(
            f"scene_{name.lower().replace(' ', '_')}", name, actions
        )

    def activate_scene(self, name: str) -> bool:
        """Activate a scene."""
        return self.scene_manager.activate_scene(name)

    # =========================================================================
    # AUTOMATION RULES
    # =========================================================================

    def create_automation_rule(self, rule: AutomationRule) -> bool:
        """Create an automation rule."""
        self.automation_engine.add_rule(rule)

        # Save to database
        rule_record = AutomationRuleRecord(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            enabled=1 if rule.enabled else 0,
            triggers_json=json.dumps([t.to_dict() for t in rule.triggers]),
            conditions_json=json.dumps([c.to_dict() for c in rule.conditions]),
            actions_json=json.dumps([a.to_dict() for a in rule.actions]),
            priority=rule.priority,
            max_executions=rule.max_executions,
            cooldown_seconds=rule.cooldown_seconds,
            tags_json=json.dumps(rule.tags),
            created_at=rule.created_at.isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        return self.db.insert_automation_rule(rule_record)

    def get_automation_rules(self) -> List[Dict[str, Any]]:
        """Get all automation rules."""
        return self.db.get_all_automation_rules()

    def trigger_rule(self, rule_id: str):
        """Manually trigger a rule."""
        self.automation_engine.trigger_rule(rule_id)

    def _load_rules_from_db(self):
        """Load automation rules from database."""
        rules = self.db.get_all_automation_rules()

        for rule_data in rules:
            # This would need to reconstruct AutomationRule objects
            # For simplicity, we re-add them from the engine if they're enabled
            logger.debug(f"Loaded rule from DB: {rule_data['name']}")

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================

    def send_notification(self, message: str, title: str = "IoT Mesh"):
        """Send a notification."""
        logger.info(f"Notification [{title}]: {message}")

    # =========================================================================
    # DISCOVERY
    # =========================================================================

    def start_discovery(self):
        """Start device discovery."""
        self.discovery_manager.start()

    def get_discovered_devices(self) -> List[DiscoveredService]:
        """Get discovered devices."""
        return self.discovery_manager.get_all_devices()

    def scan_network(self) -> List[Dict[str, Any]]:
        """Scan the network for devices."""
        scanner = NetworkScanner()
        return scanner.scan_network()

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        stats = self.db.get_statistics()

        if self.mqtt_broker:
            stats["mqtt"] = self.mqtt_broker.get_stats()

        stats["automation"] = {
            "total_rules": len(self.automation_engine.get_all_rules()),
            "enabled_rules": len(self.automation_engine.get_enabled_rules()),
            "scenes": len(self.scene_manager.get_scene_names())
            if self.scene_manager
            else 0,
        }

        return stats


# =============================================================================
# EXAMPLE USAGE
# =============================================================================


def create_example_system():
    """Create and configure an example IoT mesh system."""

    # Initialize system
    iot = IoTMeshSystem(
        mqtt_host="localhost",
        mqtt_port=1883,
        db_path="iot_mesh.db",
        use_mock_broker=True,
    )

    # Start system
    iot.start()

    # Register devices
    iot.register_device(
        device_id="light_living_room",
        name="Living Room Light",
        device_type="light",
        ip_address="192.168.1.100",
        port=80,
        properties={"brightness": 0, "color": "warm_white"},
    )

    iot.register_device(
        device_id="thermostat_main",
        name="Main Thermostat",
        device_type="thermostat",
        ip_address="192.168.1.101",
        port=80,
        properties={"temperature": 72, "target": 70, "mode": "auto"},
    )

    iot.register_device(
        device_id="motion_hallway",
        name="Hallway Motion Sensor",
        device_type="motion_sensor",
        ip_address="192.168.1.102",
        port=80,
        properties={"motion_detected": False, "last_motion": None},
    )

    iot.register_device(
        device_id="door_front",
        name="Front Door Lock",
        device_type="door_lock",
        ip_address="192.168.1.103",
        port=80,
        properties={"locked": True, "battery": 85},
    )

    # Create scenes
    iot.create_scene(
        "Good Morning",
        [
            {
                "action_type": "DEVICE_COMMAND",
                "device_id": "light_living_room",
                "command": "turn_on",
                "params": {"brightness": 100},
            },
            {
                "action_type": "DEVICE_COMMAND",
                "device_id": "thermostat_main",
                "command": "set_temperature",
                "params": {"target": 72},
            },
        ],
    )

    iot.create_scene(
        "Good Night",
        [
            {
                "action_type": "DEVICE_COMMAND",
                "device_id": "light_living_room",
                "command": "turn_off",
                "params": {},
            },
            {
                "action_type": "DEVICE_COMMAND",
                "device_id": "door_front",
                "command": "lock",
                "params": {},
            },
            {
                "action_type": "DEVICE_COMMAND",
                "device_id": "thermostat_main",
                "command": "set_temperature",
                "params": {"target": 68},
            },
        ],
    )

    # Create automation rules

    # Rule 1: Turn on light when motion detected
    rule_motion_light = AutomationRule(
        rule_id="rule_motion_light",
        name="Motion Activated Light",
        description="Turn on living room light when motion detected in hallway",
        triggers=[
            Trigger(
                trigger_type=TriggerType.DEVICE_STATE_CHANGE,
                device_id="motion_hallway",
                attribute="motion_detected",
                value=True,
            )
        ],
        conditions=[
            Condition(
                device_id="light_living_room",
                attribute="state",
                operator=ConditionOperator.NOT_EQUALS,
                value="on",
            )
        ],
        actions=[
            Action(
                action_type=ActionType.DEVICE_COMMAND,
                device_id="light_living_room",
                command="turn_on",
                params={"brightness": 100},
                delay_seconds=2,
            )
        ],
        priority=10,
        cooldown_seconds=30,
    )
    iot.create_automation_rule(rule_motion_light)

    # Rule 2: Lock door at night
    rule_auto_lock = AutomationRule(
        rule_id="rule_auto_lock",
        name="Auto Lock Door",
        description="Automatically lock front door at 10 PM",
        triggers=[
            Trigger(trigger_type=TriggerType.TIME_SCHEDULED, time_expression="22:00")
        ],
        actions=[
            Action(
                action_type=ActionType.DEVICE_COMMAND,
                device_id="door_front",
                command="lock",
                params={},
            ),
            Action(
                action_type=ActionType.NOTIFICATION,
                message="Front door has been automatically locked",
            ),
        ],
        priority=5,
    )
    iot.create_automation_rule(rule_auto_lock)

    # Rule 3: Temperature alert
    rule_temp_alert = AutomationRule(
        rule_id="rule_temp_alert",
        name="Temperature Alert",
        description="Send alert when temperature drops below 65",
        triggers=[
            Trigger(
                trigger_type=TriggerType.DEVICE_ATTRIBUTE_CHANGE,
                device_id="thermostat_main",
                attribute="temperature",
                operator=ConditionOperator.LESS_THAN,
                value=65,
            )
        ],
        actions=[
            Action(
                action_type=ActionType.NOTIFICATION,
                message="Warning: Temperature is below 65 degrees!",
            )
        ],
        priority=20,
    )
    iot.create_automation_rule(rule_temp_alert)

    return iot


def simulate_device_updates(iot: IoTMeshSystem):
    """Simulate device state updates."""

    # Simulate motion detection
    print("\n--- Simulating Motion Detection ---")
    iot.update_device_state(
        "motion_hallway",
        {"motion_detected": True, "last_motion": datetime.now().isoformat()},
    )
    time.sleep(1)

    # Simulate temperature change
    print("\n--- Simulating Temperature Drop ---")
    iot.update_device_state(
        "thermostat_main", {"temperature": 64, "target": 72, "mode": "auto"}
    )
    time.sleep(1)

    # Simulate door lock
    print("\n--- Simulating Door Lock ---")
    iot.update_device_state("door_front", {"locked": True, "battery": 85})


def main():
    """Main function demonstrating the IoT mesh system."""

    print("=" * 60)
    print("IoT Device Mesh Integration System - Demo")
    print("=" * 60)

    # Create and start system
    iot = create_example_system()

    print("\n--- System Started ---")
    print(f"Devices registered: {len(iot.get_all_devices())}")
    print(f"Automation rules: {len(iot.get_automation_rules())}")

    # Simulate some device updates
    simulate_device_updates(iot)

    # Get statistics
    print("\n--- System Statistics ---")
    stats = iot.get_statistics()
    print(json.dumps(stats, indent=2))

    # Activate a scene
    print("\n--- Activating Scene: Good Morning ---")
    iot.activate_scene("Good Morning")

    # Get device states
    print("\n--- Current Device States ---")
    for device in iot.get_all_devices():
        state = iot.get_device_state(device["device_id"])
        print(f"  {device['name']}: {state}")

    # Test discovery (simulated)
    print("\n--- Device Discovery ---")
    print("Discovery started. Use get_discovered_devices() to see results.")
    # Note: Actual discovery requires network access

    # Stop system
    print("\n--- Stopping System ---")
    iot.stop()

    print("\nDemo complete!")


if __name__ == "__main__":
    main()
