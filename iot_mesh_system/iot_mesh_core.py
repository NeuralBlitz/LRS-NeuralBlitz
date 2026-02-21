"""
IoT Device Mesh Integration System
=====================================
Comprehensive IoT infrastructure with MQTT broker, device discovery, and smart home automation.

Author: NeuralBlitz Systems
Version: 1.0.0
"""

import asyncio
import json
import logging
import socket
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
import paho.mqtt.client as mqtt
import zeroconf
from zeroconf import ServiceBrowser, Zeroconf

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS AND ENUMS
# ============================================================================


class DeviceType(Enum):
    """Supported IoT device types."""

    LIGHT = auto()
    THERMOSTAT = auto()
    CAMERA = auto()
    DOOR_LOCK = auto()
    MOTION_SENSOR = auto()
    TEMPERATURE_SENSOR = auto()
    HUMIDITY_SENSOR = auto()
    SMART_SWITCH = auto()
    SPEAKER = auto()
    GENERIC = auto()


class DeviceState(Enum):
    """Device connection states."""

    OFFLINE = auto()
    ONLINE = auto()
    CONNECTING = auto()
    ERROR = auto()


@dataclass
class DeviceCapabilities:
    """Device capability definitions."""

    can_turn_on_off: bool = False
    can_dim: bool = False
    can_change_color: bool = False
    can_report_temperature: bool = False
    can_report_humidity: bool = False
    can_detect_motion: bool = False
    can_stream_video: bool = False
    can_lock_unlock: bool = False
    supports_scheduling: bool = False
    supports_scenes: bool = False


@dataclass
class IoTDevice:
    """IoT Device data model."""

    device_id: str
    name: str
    device_type: DeviceType
    ip_address: str
    mac_address: str
    port: int
    protocol: str
    state: DeviceState = DeviceState.OFFLINE
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    properties: Dict[str, Any] = field(default_factory=dict)
    last_seen: datetime = field(default_factory=datetime.now)
    mqtt_topic: str = ""
    firmware_version: str = "unknown"
    manufacturer: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.name,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "port": self.port,
            "protocol": self.protocol,
            "state": self.state.name,
            "capabilities": {k: v for k, v in self.capabilities.__dict__.items()},
            "properties": self.properties,
            "last_seen": self.last_seen.isoformat(),
            "mqtt_topic": self.mqtt_topic,
            "firmware_version": self.firmware_version,
            "manufacturer": self.manufacturer,
        }


@dataclass
class AutomationRule:
    """Smart home automation rule."""

    rule_id: str
    name: str
    enabled: bool = True
    trigger_type: str = "schedule"  # schedule, event, sensor
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


# ============================================================================
# MQTT BROKER MANAGER
# ============================================================================


class MQTTBrokerManager:
    """
    Manages MQTT broker connections and message routing.
    Supports both embedded broker and external broker connections.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.device_registry: Dict[str, IoTDevice] = {}

    def connect(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client = mqtt.Client(client_id=f"neuralblitz_iot_{int(time.time())}")

            if username and password:
                self.client.username_pw_set(username, password)

            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # Connect with retry logic
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()

            # Wait for connection
            timeout = 10
            start = time.time()
            while not self.connected and time.time() - start < timeout:
                time.sleep(0.1)

            if self.connected:
                logger.info(
                    f"✓ Connected to MQTT broker at {self.broker_host}:{self.broker_port}"
                )
                return True
            else:
                logger.error("✗ Failed to connect to MQTT broker within timeout")
                return False

        except Exception as e:
            logger.error(f"✗ MQTT connection error: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self.connected = True
            logger.info("✓ MQTT broker connection established")

            # Subscribe to device discovery topic
            self.subscribe("iot/discovery/+", self._handle_discovery)
            self.subscribe("iot/devices/+/status", self._handle_status)
            self.subscribe("iot/devices/+/telemetry", self._handle_telemetry)
        else:
            logger.error(f"✗ MQTT connection failed with code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self.connected = False
        logger.warning(f"⚠ MQTT broker disconnected (code: {rc})")

    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        # Route to subscribers
        for pattern, handlers in self.subscriptions.items():
            if self._topic_matches(pattern, topic):
                for handler in handlers:
                    try:
                        handler(topic, payload)
                    except Exception as e:
                        logger.error(f"✗ Message handler error: {e}")

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern with wildcards."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        if len(pattern_parts) != len(topic_parts):
            return False

        for p, t in zip(pattern_parts, topic_parts):
            if p == "+":
                continue
            elif p == "#":
                return True
            elif p != t:
                return False

        return True

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to MQTT topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            if self.connected and self.client:
                self.client.subscribe(topic)

        self.subscriptions[topic].append(callback)
        logger.info(f"✓ Subscribed to: {topic}")

    def publish(
        self, topic: str, payload: Any, qos: int = 0, retain: bool = False
    ) -> bool:
        """Publish message to MQTT topic."""
        if not self.connected or not self.client:
            logger.error("✗ Cannot publish: not connected to broker")
            return False

        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            elif not isinstance(payload, str):
                payload = str(payload)

            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            logger.error(f"✗ Publish error: {e}")
            return False

    def _handle_discovery(self, topic: str, payload: str):
        """Handle device discovery messages."""
        try:
            data = json.loads(payload)
            device_id = data.get("device_id")

            if device_id:
                logger.info(f"📡 Device discovered via MQTT: {device_id}")
                self.publish(
                    f"iot/discovery/{device_id}/ack", {"status": "acknowledged"}
                )
        except json.JSONDecodeError:
            logger.warning(f"⚠ Invalid discovery payload: {payload}")

    def _handle_status(self, topic: str, payload: str):
        """Handle device status updates."""
        try:
            data = json.loads(payload)
            device_id = topic.split("/")[2]

            if device_id in self.device_registry:
                device = self.device_registry[device_id]
                device.properties.update(data.get("properties", {}))
                device.last_seen = datetime.now()

                state_str = data.get("state", "OFFLINE")
                device.state = (
                    DeviceState[state_str]
                    if state_str in DeviceState.__members__
                    else DeviceState.ERROR
                )

                logger.debug(f"📊 Status update from {device_id}: {data}")
        except Exception as e:
            logger.error(f"✗ Status handler error: {e}")

    def _handle_telemetry(self, topic: str, payload: str):
        """Handle device telemetry data."""
        try:
            data = json.loads(payload)
            device_id = topic.split("/")[2]
            logger.debug(f"📈 Telemetry from {device_id}: {data}")
        except Exception as e:
            logger.error(f"✗ Telemetry handler error: {e}")

    def register_device(self, device: IoTDevice) -> None:
        """Register device with MQTT broker."""
        self.device_registry[device.device_id] = device

        # Set up device-specific topics
        device.mqtt_topic = f"iot/devices/{device.device_id}"
        self.subscribe(f"{device.mqtt_topic}/+", lambda t, p: None)

        # Publish device registration
        self.publish("iot/registry/devices", device.to_dict(), retain=True)

        logger.info(f"✓ Device registered: {device.name} ({device.device_id})")

    def send_command(
        self, device_id: str, command: str, params: Dict[str, Any] = None
    ) -> bool:
        """Send command to device via MQTT."""
        topic = f"iot/devices/{device_id}/command"
        payload = {
            "command": command,
            "params": params or {},
            "timestamp": datetime.now().isoformat(),
        }

        return self.publish(topic, payload, qos=1)

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("✓ Disconnected from MQTT broker")


# ============================================================================
# DEVICE DISCOVERY SERVICE
# ============================================================================


class DiscoveryListener:
    """Zeroconf service discovery listener."""

    def __init__(self, registry: "DeviceRegistry"):
        self.registry = registry
        self.discovered_devices: Set[str] = set()

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle service removal."""
        logger.info(f"🔴 Service removed: {name}")
        device_id = name.split(".")[0]
        if device_id in self.registry.devices:
            self.registry.devices[device_id].state = DeviceState.OFFLINE

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle service discovery."""
        try:
            info = zc.get_service_info(type_, name)
            if info:
                device_id = name.split(".")[0]

                if device_id not in self.discovered_devices:
                    self.discovered_devices.add(device_id)

                    # Parse service info
                    properties = {}
                    if info.properties:
                        for key, value in info.properties.items():
                            try:
                                properties[key.decode("utf-8")] = value.decode("utf-8")
                            except:
                                pass

                    # Extract IP address
                    ip_address = ""
                    if info.addresses:
                        ip_address = socket.inet_ntoa(info.addresses[0])

                    # Create device entry
                    device = IoTDevice(
                        device_id=device_id,
                        name=properties.get("name", device_id),
                        device_type=DeviceType[properties.get("type", "GENERIC")],
                        ip_address=ip_address,
                        mac_address=properties.get("mac", "unknown"),
                        port=info.port,
                        protocol="mdns",
                        state=DeviceState.ONLINE,
                        capabilities=self._parse_capabilities(properties),
                        properties=properties,
                        manufacturer=properties.get("manufacturer", "unknown"),
                        firmware_version=properties.get("version", "unknown"),
                    )

                    self.registry.register_device(device)
                    logger.info(
                        f"🟢 Discovered via mDNS: {device.name} at {ip_address}:{info.port}"
                    )

        except Exception as e:
            logger.error(f"✗ Service discovery error: {e}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle service update."""
        logger.debug(f"🔄 Service updated: {name}")

    def _parse_capabilities(self, properties: Dict[str, str]) -> DeviceCapabilities:
        """Parse device capabilities from service properties."""
        caps = DeviceCapabilities()

        caps.can_turn_on_off = (
            properties.get("power_control", "false").lower() == "true"
        )
        caps.can_dim = properties.get("dimming", "false").lower() == "true"
        caps.can_change_color = (
            properties.get("color_control", "false").lower() == "true"
        )
        caps.can_report_temperature = (
            properties.get("temperature", "false").lower() == "true"
        )
        caps.can_report_humidity = properties.get("humidity", "false").lower() == "true"
        caps.can_detect_motion = properties.get("motion", "false").lower() == "true"
        caps.can_stream_video = properties.get("video", "false").lower() == "true"
        caps.can_lock_unlock = properties.get("lock", "false").lower() == "true"

        return caps


class SSDPDiscovery:
    """SSDP (Simple Service Discovery Protocol) implementation."""

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900

    def __init__(self, registry: "DeviceRegistry"):
        self.registry = registry
        self.running = False
        self.discovery_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start SSDP discovery."""
        self.running = True
        self.discovery_thread = threading.Thread(
            target=self._discovery_loop, daemon=True
        )
        self.discovery_thread.start()
        logger.info("✓ SSDP discovery started")

    def stop(self) -> None:
        """Stop SSDP discovery."""
        self.running = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=2)
        logger.info("✓ SSDP discovery stopped")

    def _discovery_loop(self) -> None:
        """Main SSDP discovery loop."""
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Join multicast group
        mreq = socket.inet_aton(self.SSDP_ADDR) + socket.inet_aton("0.0.0.0")
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        sock.bind(("", self.SSDP_PORT))
        sock.settimeout(1)

        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                self._process_ssdp_message(data.decode("utf-8", errors="ignore"), addr)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"✗ SSDP error: {e}")

        sock.close()

    def _process_ssdp_message(self, message: str, addr: tuple) -> None:
        """Process SSDP message."""
        lines = message.split("\r\n")

        # Check if it's a NOTIFY or M-SEARCH response
        if lines[0].startswith("NOTIFY") or "200 OK" in lines[0]:
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().upper()] = value.strip()

            usn = headers.get("USN", "")
            location = headers.get("LOCATION", "")

            if usn and location:
                device_id = usn.split(":")[-1] if ":" in usn else usn

                if device_id not in [
                    d.device_id for d in self.registry.devices.values()
                ]:
                    # Create basic device entry from SSDP info
                    device = IoTDevice(
                        device_id=device_id,
                        name=f"SSDP-{device_id[:8]}",
                        device_type=DeviceType.GENERIC,
                        ip_address=addr[0],
                        mac_address="unknown",
                        port=addr[1],
                        protocol="ssdp",
                        state=DeviceState.ONLINE,
                        properties={"ssdp_location": location, "ssdp_usn": usn},
                    )

                    self.registry.register_device(device)
                    logger.info(f"🟢 Discovered via SSDP: {device_id} at {addr[0]}")

    def send_msearch(self) -> None:
        """Send M-SEARCH discovery request."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        search_request = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {self.SSDP_ADDR}:{self.SSDP_PORT}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 3\r\n"
            "ST: ssdp:all\r\n"
            "\r\n"
        )

        sock.sendto(search_request.encode(), (self.SSDP_ADDR, self.SSDP_PORT))

        # Collect responses
        start = time.time()
        while time.time() - start < 3:
            try:
                data, addr = sock.recvfrom(4096)
                self._process_ssdp_message(data.decode("utf-8", errors="ignore"), addr)
            except socket.timeout:
                break

        sock.close()


class DeviceRegistry:
    """Central device registry and management."""

    def __init__(self):
        self.devices: Dict[str, IoTDevice] = {}
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        self.ssdp: Optional[SSDPDiscovery] = None
        self.listeners: List[Callable] = []

    def register_device(self, device: IoTDevice) -> None:
        """Register a new device."""
        is_new = device.device_id not in self.devices
        self.devices[device.device_id] = device

        if is_new:
            logger.info(
                f"✓ Device registered: {device.name} ({device.device_type.name})"
            )
            self._notify_listeners("device_added", device)
        else:
            self._notify_listeners("device_updated", device)

    def unregister_device(self, device_id: str) -> None:
        """Unregister a device."""
        if device_id in self.devices:
            device = self.devices.pop(device_id)
            logger.info(f"✗ Device unregistered: {device.name}")
            self._notify_listeners("device_removed", device)

    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get device by ID."""
        return self.devices.get(device_id)

    def get_devices_by_type(self, device_type: DeviceType) -> List[IoTDevice]:
        """Get all devices of a specific type."""
        return [d for d in self.devices.values() if d.device_type == device_type]

    def get_online_devices(self) -> List[IoTDevice]:
        """Get all online devices."""
        return [d for d in self.devices.values() if d.state == DeviceState.ONLINE]

    def add_listener(self, callback: Callable) -> None:
        """Add device event listener."""
        self.listeners.append(callback)

    def _notify_listeners(self, event: str, device: IoTDevice) -> None:
        """Notify all listeners of device event."""
        for listener in self.listeners:
            try:
                listener(event, device)
            except Exception as e:
                logger.error(f"✗ Listener error: {e}")

    def start_discovery(self) -> None:
        """Start all discovery protocols."""
        # Start mDNS discovery
        self.zeroconf = Zeroconf()
        listener = DiscoveryListener(self)
        self.browser = ServiceBrowser(
            self.zeroconf, "_iot-device._tcp.local.", listener
        )
        logger.info("✓ mDNS discovery started")

        # Start SSDP discovery
        self.ssdp = SSDPDiscovery(self)
        self.ssdp.start()

        # Send initial M-SEARCH
        self.ssdp.send_msearch()

    def stop_discovery(self) -> None:
        """Stop all discovery protocols."""
        if self.browser:
            self.browser.cancel()

        if self.zeroconf:
            self.zeroconf.close()

        if self.ssdp:
            self.ssdp.stop()

        logger.info("✓ Discovery protocols stopped")

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dictionary."""
        return {
            "device_count": len(self.devices),
            "online_count": len(self.get_online_devices()),
            "devices": {k: v.to_dict() for k, v in self.devices.items()},
        }


# ============================================================================
# SMART HOME AUTOMATION ENGINE
# ============================================================================


class SmartHomeAutomation:
    """
    Smart home automation engine with rule processing and scene management.
    """

    def __init__(
        self, mqtt_manager: MQTTBrokerManager, device_registry: DeviceRegistry
    ):
        self.mqtt = mqtt_manager
        self.registry = device_registry
        self.rules: Dict[str, AutomationRule] = {}
        self.scenes: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.sensor_states: Dict[str, Any] = {}

    def start(self) -> None:
        """Start automation engine."""
        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        # Subscribe to sensor events
        self.mqtt.subscribe("iot/devices/+/sensors/+", self._handle_sensor_event)

        logger.info("✓ Smart home automation engine started")

    def stop(self) -> None:
        """Stop automation engine."""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2)
        logger.info("✓ Smart home automation engine stopped")

    def _scheduler_loop(self) -> None:
        """Main automation scheduler loop."""
        while self.running:
            try:
                self._process_scheduled_rules()
                time.sleep(1)
            except Exception as e:
                logger.error(f"✗ Scheduler error: {e}")

    def _process_scheduled_rules(self) -> None:
        """Process time-based automation rules."""
        now = datetime.now()

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.trigger_type == "schedule":
                self._check_schedule_trigger(rule, now)

    def _check_schedule_trigger(self, rule: AutomationRule, now: datetime) -> None:
        """Check if scheduled rule should trigger."""
        config = rule.trigger_config

        # Check time-based triggers
        if "time" in config:
            trigger_time = config["time"]
            current_time = now.strftime("%H:%M")

            if current_time == trigger_time:
                # Check if we've already triggered this minute
                if rule.last_triggered and (now - rule.last_triggered).seconds < 60:
                    return

                if self._evaluate_conditions(rule.conditions):
                    self._execute_actions(rule)
                    rule.last_triggered = now
                    rule.trigger_count += 1
                    logger.info(f"🕐 Scheduled rule triggered: {rule.name}")

        # Check interval-based triggers
        elif "interval_seconds" in config:
            interval = config["interval_seconds"]
            if rule.last_triggered:
                elapsed = (now - rule.last_triggered).total_seconds()
                if elapsed >= interval:
                    if self._evaluate_conditions(rule.conditions):
                        self._execute_actions(rule)
                        rule.last_triggered = now
                        rule.trigger_count += 1

    def _handle_sensor_event(self, topic: str, payload: str) -> None:
        """Handle sensor state change events."""
        try:
            data = json.loads(payload)
            parts = topic.split("/")
            device_id = parts[2]
            sensor_type = parts[4]

            # Update sensor state
            self.sensor_states[f"{device_id}.{sensor_type}"] = data

            # Check event-based rules
            for rule in self.rules.values():
                if rule.enabled and rule.trigger_type == "sensor":
                    self._check_sensor_trigger(rule, device_id, sensor_type, data)

        except Exception as e:
            logger.error(f"✗ Sensor event handler error: {e}")

    def _check_sensor_trigger(
        self, rule: AutomationRule, device_id: str, sensor_type: str, data: Dict
    ) -> None:
        """Check if sensor-based rule should trigger."""
        config = rule.trigger_config

        # Check device and sensor match
        if (
            config.get("device_id") == device_id
            and config.get("sensor_type") == sensor_type
        ):
            # Check threshold if specified
            if "threshold" in config and "value" in data:
                threshold = config["threshold"]
                value = data["value"]
                operator = config.get("operator", "gt")

                triggered = False
                if operator == "gt" and value > threshold:
                    triggered = True
                elif operator == "lt" and value < threshold:
                    triggered = True
                elif operator == "eq" and value == threshold:
                    triggered = True

                if triggered and self._evaluate_conditions(rule.conditions):
                    self._execute_actions(rule)
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
                    logger.info(f"📡 Sensor rule triggered: {rule.name}")

    def _evaluate_conditions(self, conditions: List[Dict[str, Any]]) -> bool:
        """Evaluate rule conditions."""
        if not conditions:
            return True

        for condition in conditions:
            condition_type = condition.get("type")

            if condition_type == "time_range":
                now = datetime.now()
                start = condition.get("start")
                end = condition.get("end")
                current_time = now.strftime("%H:%M")

                if start and end:
                    if not (start <= current_time <= end):
                        return False

            elif condition_type == "device_state":
                device_id = condition.get("device_id")
                required_state = condition.get("state")

                device = self.registry.get_device(device_id)
                if not device or device.state.name != required_state:
                    return False

            elif condition_type == "sensor_value":
                sensor_key = condition.get("sensor")
                operator = condition.get("operator", "eq")
                value = condition.get("value")

                current_value = self.sensor_states.get(sensor_key)
                if current_value is None:
                    return False

                if operator == "eq" and current_value != value:
                    return False
                elif operator == "gt" and current_value <= value:
                    return False
                elif operator == "lt" and current_value >= value:
                    return False

        return True

    def _execute_actions(self, rule: AutomationRule) -> None:
        """Execute rule actions."""
        for action in rule.actions:
            action_type = action.get("type")

            try:
                if action_type == "device_command":
                    device_id = action.get("device_id")
                    command = action.get("command")
                    params = action.get("params", {})

                    self.mqtt.send_command(device_id, command, params)
                    logger.info(f"📤 Command sent to {device_id}: {command}")

                elif action_type == "scene_activate":
                    scene_name = action.get("scene")
                    self.activate_scene(scene_name)

                elif action_type == "notification":
                    message = action.get("message")
                    self._send_notification(message)

                elif action_type == "delay":
                    delay_seconds = action.get("seconds", 0)
                    time.sleep(delay_seconds)

            except Exception as e:
                logger.error(f"✗ Action execution error: {e}")

    def add_rule(self, rule: AutomationRule) -> None:
        """Add automation rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"✓ Automation rule added: {rule.name}")

    def remove_rule(self, rule_id: str) -> None:
        """Remove automation rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"✓ Automation rule removed: {rule_id}")

    def create_scene(self, name: str, device_states: Dict[str, Dict[str, Any]]) -> None:
        """Create automation scene."""
        self.scenes[name] = device_states
        logger.info(f"✓ Scene created: {name}")

    def activate_scene(self, name: str) -> bool:
        """Activate a scene."""
        if name not in self.scenes:
            logger.warning(f"⚠ Scene not found: {name}")
            return False

        device_states = self.scenes[name]
        logger.info(f"🎬 Activating scene: {name}")

        for device_id, state in device_states.items():
            device = self.registry.get_device(device_id)
            if device and device.state == DeviceState.ONLINE:
                # Determine command based on device capabilities
                if device.capabilities.can_turn_on_off and "power" in state:
                    command = "turn_on" if state["power"] else "turn_off"
                    self.mqtt.send_command(device_id, command)

                if device.capabilities.can_dim and "brightness" in state:
                    self.mqtt.send_command(
                        device_id, "set_brightness", {"value": state["brightness"]}
                    )

                if device.capabilities.can_change_color and "color" in state:
                    self.mqtt.send_command(
                        device_id, "set_color", {"color": state["color"]}
                    )

        return True

    def _send_notification(self, message: str) -> None:
        """Send notification via MQTT."""
        self.mqtt.publish(
            "iot/notifications/automation",
            {
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "priority": "normal",
            },
        )

    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of all automation rules."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "triggered_count": sum(r.trigger_count for r in self.rules.values()),
            "scenes": list(self.scenes.keys()),
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "enabled": r.enabled,
                    "trigger_type": r.trigger_type,
                    "trigger_count": r.trigger_count,
                    "last_triggered": r.last_triggered.isoformat()
                    if r.last_triggered
                    else None,
                }
                for r in self.rules.values()
            ],
        }


# ============================================================================
# DEVICE CONTROLLERS
# ============================================================================


class DeviceController(ABC):
    """Abstract base class for device controllers."""

    def __init__(self, mqtt_manager: MQTTBrokerManager):
        self.mqtt = mqtt_manager

    @abstractmethod
    def turn_on(self, device_id: str) -> bool:
        pass

    @abstractmethod
    def turn_off(self, device_id: str) -> bool:
        pass


class LightController(DeviceController):
    """Controller for smart lights."""

    def turn_on(self, device_id: str) -> bool:
        return self.mqtt.send_command(device_id, "turn_on")

    def turn_off(self, device_id: str) -> bool:
        return self.mqtt.send_command(device_id, "turn_off")

    def set_brightness(self, device_id: str, brightness: int) -> bool:
        """Set light brightness (0-100)."""
        return self.mqtt.send_command(
            device_id, "set_brightness", {"value": brightness}
        )

    def set_color(self, device_id: str, color: str) -> bool:
        """Set light color (hex or name)."""
        return self.mqtt.send_command(device_id, "set_color", {"color": color})

    def set_temperature(self, device_id: str, temperature: int) -> bool:
        """Set color temperature in Kelvin."""
        return self.mqtt.send_command(
            device_id, "set_temperature", {"temperature": temperature}
        )


class ThermostatController(DeviceController):
    """Controller for smart thermostats."""

    def turn_on(self, device_id: str) -> bool:
        return self.mqtt.send_command(device_id, "turn_on")

    def turn_off(self, device_id: str) -> bool:
        return self.mqtt.send_command(device_id, "turn_off")

    def set_temperature(self, device_id: str, temperature: float) -> bool:
        """Set target temperature."""
        return self.mqtt.send_command(
            device_id, "set_temperature", {"temperature": temperature}
        )

    def set_mode(self, device_id: str, mode: str) -> bool:
        """Set thermostat mode (heat, cool, auto, off)."""
        return self.mqtt.send_command(device_id, "set_mode", {"mode": mode})


class DoorLockController(DeviceController):
    """Controller for smart door locks."""

    def turn_on(self, device_id: str) -> bool:
        """Lock the door."""
        return self.mqtt.send_command(device_id, "lock")

    def turn_off(self, device_id: str) -> bool:
        """Unlock the door."""
        return self.mqtt.send_command(device_id, "unlock")

    def lock(self, device_id: str) -> bool:
        return self.turn_on(device_id)

    def unlock(self, device_id: str) -> bool:
        return self.turn_off(device_id)


# ============================================================================
# MAIN IoT MESH SYSTEM
# ============================================================================


class IoTMeshSystem:
    """
    Main IoT Device Mesh Integration System.
    Orchestrates MQTT broker, device discovery, and smart home automation.
    """

    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883):
        self.mqtt = MQTTBrokerManager(mqtt_host, mqtt_port)
        self.registry = DeviceRegistry()
        self.automation = SmartHomeAutomation(self.mqtt, self.registry)

        # Device controllers
        self.light_controller = LightController(self.mqtt)
        self.thermostat_controller = ThermostatController(self.mqtt)
        self.doorlock_controller = DoorLockController(self.mqtt)

        # System state
        self.running = False
        self.start_time: Optional[datetime] = None

        # Add registry listener for MQTT registration
        self.registry.add_listener(self._on_device_event)

    def start(self) -> bool:
        """Start the IoT mesh system."""
        logger.info("🚀 Starting IoT Device Mesh Integration System...")

        # Connect to MQTT broker
        if not self.mqtt.connect():
            logger.error("✗ Failed to start: MQTT connection failed")
            return False

        # Start device discovery
        self.registry.start_discovery()

        # Start automation engine
        self.automation.start()

        self.running = True
        self.start_time = datetime.now()

        logger.info("✅ IoT Mesh System started successfully")
        return True

    def stop(self) -> None:
        """Stop the IoT mesh system."""
        logger.info("🛑 Stopping IoT Device Mesh Integration System...")

        self.running = False

        # Stop automation engine
        self.automation.stop()

        # Stop device discovery
        self.registry.stop_discovery()

        # Disconnect from MQTT
        self.mqtt.disconnect()

        logger.info("✅ IoT Mesh System stopped")

    def _on_device_event(self, event: str, device: IoTDevice) -> None:
        """Handle device registry events."""
        if event == "device_added":
            # Register device with MQTT broker
            self.mqtt.register_device(device)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        uptime = None
        if self.start_time:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            uptime = {
                "seconds": int(uptime_seconds),
                "formatted": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s",
            }

        return {
            "system": {
                "running": self.running,
                "started_at": self.start_time.isoformat() if self.start_time else None,
                "uptime": uptime,
                "version": "1.0.0",
            },
            "mqtt": {
                "connected": self.mqtt.connected,
                "broker": f"{self.mqtt.broker_host}:{self.mqtt.broker_port}",
                "subscriptions": len(self.mqtt.subscriptions),
                "registered_devices": len(self.mqtt.device_registry),
            },
            "discovery": {
                "active": self.registry.zeroconf is not None,
                "discovered_devices": len(self.registry.devices),
                "online_devices": len(self.registry.get_online_devices()),
            },
            "automation": self.automation.get_rules_summary(),
            "devices": self.registry.to_dict(),
        }

    def create_default_automation_rules(self) -> None:
        """Create sample automation rules."""
        # Rule 1: Turn on lights at sunset
        rule1 = AutomationRule(
            rule_id="lights_at_sunset",
            name="Evening Lights",
            trigger_type="schedule",
            trigger_config={"time": "18:00"},
            conditions=[{"type": "time_range", "start": "16:00", "end": "23:59"}],
            actions=[
                {
                    "type": "device_command",
                    "device_id": "living_room_light",
                    "command": "turn_on",
                },
                {
                    "type": "device_command",
                    "device_id": "hallway_light",
                    "command": "turn_on",
                    "params": {"brightness": 50},
                },
            ],
        )
        self.automation.add_rule(rule1)

        # Rule 2: Motion-triggered lights
        rule2 = AutomationRule(
            rule_id="motion_lights",
            name="Motion-Activated Lights",
            trigger_type="sensor",
            trigger_config={
                "device_id": "entrance_motion",
                "sensor_type": "motion",
                "threshold": 1,
                "operator": "gt",
            },
            conditions=[{"type": "time_range", "start": "18:00", "end": "06:00"}],
            actions=[
                {
                    "type": "device_command",
                    "device_id": "entrance_light",
                    "command": "turn_on",
                },
                {"type": "delay", "seconds": 300},
                {
                    "type": "device_command",
                    "device_id": "entrance_light",
                    "command": "turn_off",
                },
            ],
        )
        self.automation.add_rule(rule2)

        # Rule 3: Temperature control
        rule3 = AutomationRule(
            rule_id="temp_control",
            name="Smart Temperature Control",
            trigger_type="sensor",
            trigger_config={
                "device_id": "living_room_temp",
                "sensor_type": "temperature",
                "threshold": 24.0,
                "operator": "gt",
            },
            actions=[
                {
                    "type": "device_command",
                    "device_id": "ac_unit",
                    "command": "turn_on",
                },
                {
                    "type": "device_command",
                    "device_id": "ac_unit",
                    "command": "set_temperature",
                    "params": {"temperature": 22.0},
                },
            ],
        )
        self.automation.add_rule(rule3)

        logger.info("✓ Default automation rules created")

    def create_default_scenes(self) -> None:
        """Create sample scenes."""
        # Morning scene
        self.automation.create_scene(
            "morning",
            {
                "bedroom_light": {"power": True, "brightness": 30},
                "kitchen_light": {"power": True, "brightness": 80},
                "coffee_maker": {"power": True},
                "thermostat": {"power": True, "temperature": 21},
            },
        )

        # Evening scene
        self.automation.create_scene(
            "evening",
            {
                "living_room_light": {
                    "power": True,
                    "brightness": 60,
                    "color": "warm_white",
                },
                "bedroom_light": {"power": True, "brightness": 40},
                "kitchen_light": {"power": True, "brightness": 50},
                "entrance_light": {"power": True, "brightness": 70},
            },
        )

        # Away scene
        self.automation.create_scene(
            "away",
            {
                "bedroom_light": {"power": False},
                "living_room_light": {"power": False},
                "kitchen_light": {"power": False},
                "thermostat": {"power": True, "temperature": 18},
                "security_system": {"power": True, "armed": True},
            },
        )

        logger.info("✓ Default scenes created")


# ============================================================================
# DEMO AND TESTING
# ============================================================================


def run_demo():
    """Run a demonstration of the IoT Mesh System."""
    print("\n" + "=" * 70)
    print("IoT DEVICE MESH INTEGRATION SYSTEM - DEMO")
    print("=" * 70 + "\n")

    # Create and start the system
    iot_system = IoTMeshSystem(mqtt_host="localhost", mqtt_port=1883)

    # Note: In production, you'd connect to a real MQTT broker
    # For demo purposes, we'll show the structure even without broker connection

    print("🏗️  System Components:")
    print("  ✓ MQTT Broker Manager (broker: localhost:1883)")
    print("  ✓ Device Registry with mDNS and SSDP discovery")
    print("  ✓ Smart Home Automation Engine")
    print("  ✓ Device Controllers (Light, Thermostat, DoorLock)")

    print("\n📋 Creating default automation rules...")
    iot_system.create_default_automation_rules()

    print("\n🎬 Creating default scenes...")
    iot_system.create_default_scenes()

    # Show system status
    print("\n📊 System Status Report:")
    print("-" * 50)

    status = iot_system.get_system_status()

    print(f"System Version: {status['system']['version']}")
    print(f"MQTT Broker: {status['mqtt']['broker']}")
    print(f"MQTT Connected: {status['mqtt']['connected']}")
    print(f"Discovery Active: {status['discovery']['active']}")
    print(f"Total Devices: {status['discovery']['discovered_devices']}")
    print(f"Online Devices: {status['discovery']['online_devices']}")

    print("\n🤖 Automation Rules:")
    for rule in status["automation"]["rules"]:
        print(
            f"  • {rule['name']} ({rule['trigger_type']}) - Enabled: {rule['enabled']}"
        )

    print("\n🎬 Available Scenes:")
    for scene in status["automation"]["scenes"]:
        print(f"  • {scene}")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70 + "\n")

    return iot_system


if __name__ == "__main__":
    # Run the demo
    system = run_demo()
