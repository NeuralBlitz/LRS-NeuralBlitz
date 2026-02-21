"""
IoT Device Mesh Integration System - MQTT Broker Module
======================================================
MQTT broker management, client handling, and message routing.

Author: NeuralBlitz Systems
Version: 2.0.0
"""

import asyncio
import json
import logging
import ssl
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class QoSLevel(Enum):
    """MQTT QoS levels."""

    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2


@dataclass
class MQTTMessage:
    """Represents an MQTT message."""

    topic: str
    payload: str
    qos: QoSLevel = QoSLevel.AT_MOST_ONCE
    retain: bool = False
    client_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class MQTTClientInfo:
    """Information about a connected MQTT client."""

    client_id: str
    protocol_version: int
    keepalive: int
    connected_at: datetime = field(default_factory=datetime.now)
    subscriptions: Set[str] = field(default_factory=set)
    messages_sent: int = 0
    messages_received: int = 0
    last_activity: datetime = field(default_factory=datetime.now)


class MockMQTTBroker:
    """
    Mock MQTT Broker for testing and simulation.
    Implements broker functionality without external dependencies.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        max_clients: int = 100,
        max_message_size: int = 268435456,  # 256MB
    ):
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.max_message_size = max_message_size

        self._clients: Dict[str, MQTTClientInfo] = {}
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._retained_messages: Dict[str, str] = {}
        self._message_history: List[MQTTMessage] = []
        self._message_callbacks: List[Callable[[MQTTMessage], None]] = []

        self._running = False
        self._lock = threading.RLock()

        logger.info(f"Mock MQTT Broker initialized on {host}:{port}")

    def start(self):
        """Start the MQTT broker."""
        self._running = True
        logger.info(f"MQTT Broker started on {self.host}:{self.port}")

    def stop(self):
        """Stop the MQTT broker."""
        self._running = False
        with self._lock:
            self._clients.clear()
            self._subscriptions.clear()
        logger.info("MQTT Broker stopped")

    def connect_client(
        self, client_id: str, protocol_version: int = 4, keepalive: int = 60
    ) -> bool:
        """Connect a new client to the broker."""
        with self._lock:
            if len(self._clients) >= self.max_clients:
                logger.warning(f"Max clients reached, rejecting {client_id}")
                return False

            if client_id in self._clients:
                logger.warning(f"Client {client_id} already connected")
                return False

            client_info = MQTTClientInfo(
                client_id=client_id,
                protocol_version=protocol_version,
                keepalive=keepalive,
            )
            self._clients[client_id] = client_info
            logger.info(f"Client {client_id} connected")
            return True

    def disconnect_client(self, client_id: str):
        """Disconnect a client from the broker."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                # Remove subscriptions
                for topic in list(self._subscriptions.keys()):
                    self._subscriptions[topic].discard(client_id)
                logger.info(f"Client {client_id} disconnected")

    def subscribe(
        self, client_id: str, topic: str, qos: QoSLevel = QoSLevel.AT_MOST_ONCE
    ) -> bool:
        """Subscribe a client to a topic."""
        with self._lock:
            if client_id not in self._clients:
                logger.warning(f"Client {client_id} not found")
                return False

            self._subscriptions[topic].add(client_id)
            self._clients[client_id].subscriptions.add(topic)
            self._clients[client_id].last_activity = datetime.now()
            logger.info(f"Client {client_id} subscribed to {topic}")
            return True

    def unsubscribe(self, client_id: str, topic: str) -> bool:
        """Unsubscribe a client from a topic."""
        with self._lock:
            if client_id not in self._clients:
                return False

            self._subscriptions[topic].discard(client_id)
            self._clients[client_id].subscriptions.discard(topic)
            self._clients[client_id].last_activity = datetime.now()
            logger.info(f"Client {client_id} unsubscribed from {topic}")
            return True

    def publish(
        self,
        topic: str,
        payload: str,
        qos: QoSLevel = QoSLevel.AT_MOST_ONCE,
        retain: bool = False,
        client_id: str = "broker",
    ) -> bool:
        """Publish a message to a topic."""
        with self._lock:
            if len(payload) > self.max_message_size:
                logger.warning(f"Message too large: {len(payload)} bytes")
                return False

            message = MQTTMessage(
                topic=topic,
                payload=payload,
                qos=qos,
                retain=retain,
                client_id=client_id,
            )

            self._message_history.append(message)

            # Keep only last 10000 messages
            if len(self._message_history) > 10000:
                self._message_history = self._message_history[-5000:]

            # Handle retained messages
            if retain:
                self._retained_messages[topic] = payload

            # Deliver to subscribers
            subscribers = self._subscriptions.get(topic, set())
            # Also match wildcard subscriptions
            for sub_topic, clients in self._subscriptions.items():
                if self._topic_matches(sub_topic, topic):
                    subscribers.update(clients)

            for sub_client_id in subscribers:
                if sub_client_id in self._clients:
                    self._clients[sub_client_id].messages_received += 1
                    self._clients[sub_client_id].last_activity = datetime.now()

            # Notify callbacks
            for callback in self._message_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Message callback error: {e}")

            if client_id in self._clients:
                self._clients[client_id].messages_sent += 1

            logger.debug(f"Published to {topic}: {payload[:100]}...")
            return True

    def _topic_matches(self, subscription: str, topic: str) -> bool:
        """Check if a topic matches a subscription (supports wildcards)."""
        sub_parts = subscription.split("/")
        topic_parts = topic.split("/")

        i = 0
        j = 0

        while i < len(sub_parts) and j < len(topic_parts):
            if sub_parts[i] == "#":
                return True
            elif sub_parts[i] == "+":
                i += 1
                j += 1
            elif sub_parts[i] == topic_parts[j]:
                i += 1
                j += 1
            else:
                return False

        return i == len(sub_parts) and j == len(topic_parts)

    def get_retained_message(self, topic: str) -> Optional[str]:
        """Get a retained message for a topic."""
        return self._retained_messages.get(topic)

    def get_client_info(self, client_id: str) -> Optional[MQTTClientInfo]:
        """Get information about a client."""
        return self._clients.get(client_id)

    def get_all_clients(self) -> List[MQTTClientInfo]:
        """Get all connected clients."""
        return list(self._clients.values())

    def get_subscriptions(self, topic: str) -> Set[str]:
        """Get all subscriptions for a topic."""
        return self._subscriptions.get(topic, set())

    def get_message_history(
        self, topic: Optional[str] = None, limit: int = 100
    ) -> List[MQTTMessage]:
        """Get message history."""
        if topic:
            return [
                m for m in self._message_history if self._topic_matches(topic, m.topic)
            ][-limit:]
        return self._message_history[-limit:]

    def add_message_callback(self, callback: Callable[[MQTTMessage], None]):
        """Add a callback for incoming messages."""
        self._message_callbacks.append(callback)

    def remove_message_callback(self, callback: Callable[[MQTTMessage], None]):
        """Remove a message callback."""
        if callback in self._message_callbacks:
            self._message_callbacks.remove(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            "connected_clients": len(self._clients),
            "total_topics": len(self._subscriptions),
            "retained_messages": len(self._retained_messages),
            "total_messages": len(self._message_history),
            "max_clients": self.max_clients,
        }


class MQTTClientManager:
    """
    Manages MQTT client connections and message handling.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._broker = MockMQTTBroker(broker_host, broker_port)
        self._device_topics: Dict[str, str] = {}  # device_id -> topic
        self._topic_handlers: Dict[str, List[Callable[[str, str], None]]] = defaultdict(
            list
        )
        self._running = False

        logger.info(f" MQTT Client Manager initialized for {broker_host}:{broker_port}")

    @property
    def broker(self) -> MockMQTTBroker:
        """Get the underlying broker."""
        return self._broker

    def start(self):
        """Start the MQTT client manager."""
        self._broker.start()
        self._running = True
        logger.info("MQTT Client Manager started")

    def stop(self):
        """Stop the MQTT client manager."""
        self._running = False
        self._broker.stop()
        logger.info("MQTT Client Manager stopped")

    def register_device_topic(self, device_id: str, topic: str):
        """Register a device's MQTT topic."""
        self._device_topics[device_id] = topic
        logger.info(f"Registered device {device_id} to topic {topic}")

    def publish_device_state(
        self,
        device_id: str,
        state: Dict[str, Any],
        qos: QoSLevel = QoSLevel.AT_LEAST_ONCE,
    ):
        """Publish device state to its topic."""
        topic = self._device_topics.get(device_id, f"devices/{device_id}/state")
        payload = json.dumps(state)
        self._broker.publish(topic, payload, qos, retain=True)

    def publish_command(
        self,
        device_id: str,
        command: str,
        params: Dict[str, Any] = None,
        qos: QoSLevel = QoSLevel.AT_LEAST_ONCE,
    ):
        """Publish a command to a device."""
        topic = f"devices/{device_id}/command"
        payload = json.dumps(
            {
                "command": command,
                "params": params or {},
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._broker.publish(topic, payload, qos)

    def subscribe_to_device(
        self, device_id: str, handler: Callable[[str, Dict[str, Any]], None]
    ):
        """Subscribe to device state updates."""
        topic = f"devices/{device_id}/state"
        self._broker.subscribe(f"devices/{device_id}/#", QoSLevel.AT_LEAST_ONCE)
        self._topic_handlers[device_id].append(handler)

        def message_handler(msg: MQTTMessage):
            try:
                payload = json.loads(msg.payload)
                for h in self._topic_handlers[device_id]:
                    h(device_id, payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in message: {msg.payload}")

        self._broker.add_message_callback(message_handler)

    def get_device_topic(self, device_id: str) -> str:
        """Get the MQTT topic for a device."""
        return self._device_topics.get(device_id, f"devices/{device_id}")

    def broadcast_message(self, topic: str, payload: Dict[str, Any]):
        """Broadcast a message to a topic."""
        self._broker.publish(topic, json.dumps(payload), QoSLevel.AT_LEAST_ONCE)


class MQTTClientWrapper:
    """
    Wrapper for paho-mqtt client with reconnection and error handling.
    """

    def __init__(
        self,
        client_id: str,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        keepalive: int = 60,
    ):
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.keepalive = keepalive

        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._connected = False
        self._message_callbacks: List[Callable[[str, str], None]] = []

        # Setup callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish
        self._client.on_subscribe = self._on_subscribe

        # Setup authentication
        if username and password:
            self._client.username_pw_set(username, password)

        # Setup TLS if needed
        if use_tls:
            self._client.tls_set(
                certfile=None, keyfile=None, tls_version=ssl.PROTOCOL_TLSv1_2
            )

        logger.info(f"MQTT Client {client_id} initialized")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker."""
        if rc == 0:
            self._connected = True
            logger.info(
                f"Connected to MQTT broker: {self.broker_host}:{self.broker_port}"
            )
        else:
            logger.error(f"Connection failed with code: {rc}")
            self._connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker."""
        self._connected = False
        logger.warning(f"Disconnected from MQTT broker: {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback when message received."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            for callback in self._message_callbacks:
                callback(topic, payload)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_publish(self, client, userdata, mid):
        """Callback when message published."""
        logger.debug(f"Message {mid} published")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback when subscribed."""
        logger.debug(f"Subscribed with QoS: {granted_qos}")

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        try:
            self._client.connect(self.broker_host, self.broker_port, self.keepalive)
            self._client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the MQTT broker."""
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False

    def publish(
        self, topic: str, payload: str, qos: int = 0, retain: bool = False
    ) -> int:
        """Publish a message."""
        if not self._connected:
            logger.warning("Not connected to broker")
            return -1

        result = self._client.publish(topic, payload, qos, retain)
        return result.rc

    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """Subscribe to a topic."""
        if not self._connected:
            logger.warning("Not connected to broker")
            return False

        result = self._client.subscribe(topic, qos)
        return result[0] == 0

    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic."""
        if not self._connected:
            return False

        result = self._client.unsubscribe(topic)
        return result[0] == 0

    def add_message_callback(self, callback: Callable[[str, str], None]):
        """Add a message callback."""
        self._message_callbacks.append(callback)

    def is_connected(self) -> bool:
        """Check if connected to broker."""
        return self._connected


# ============================================================================
# MQTT TOPIC UTILITIES
# ============================================================================


class MqttTopicManager:
    """Manages MQTT topic conventions and routing."""

    # Topic templates
    DEVICE_STATE = "devices/{device_id}/state"
    DEVICE_COMMAND = "devices/{device_id}/command"
    DEVICE_STATUS = "devices/{device_id}/status"
    DEVICE_TELEMETRY = "devices/{device_id}/telemetry"
    DEVICE_EVENT = "devices/{device_id}/event"

    # Group topics
    GROUP_COMMAND = "groups/{group_id}/command"
    GROUP_STATE = "groups/{group_id}/state"

    # System topics
    SYSTEM_DISCOVER = "system/discover"
    SYSTEM_STATUS = "system/status"
    SYSTEM_CONFIG = "system/config"

    # Home automation topics
    AUTOMATION_TRIGGER = "automation/{automation_id}/trigger"
    AUTOMATION_ACTION = "automation/{automation_id}/action"
    SCENE_ACTIVATE = "scenes/{scene_id}/activate"

    @staticmethod
    def get_device_state_topic(device_id: str) -> str:
        """Get the state topic for a device."""
        return MqttTopicManager.DEVICE_STATE.format(device_id=device_id)

    @staticmethod
    def get_device_command_topic(device_id: str) -> str:
        """Get the command topic for a device."""
        return MqttTopicManager.DEVICE_COMMAND.format(device_id=device_id)

    @staticmethod
    def get_device_telemetry_topic(device_id: str) -> str:
        """Get the telemetry topic for a device."""
        return MqttTopicManager.DEVICE_TELEMETRY.format(device_id=device_id)

    @staticmethod
    def parse_topic(topic: str) -> Dict[str, str]:
        """Parse a topic and extract components."""
        parts = topic.split("/")
        result = {"topic": topic, "raw_parts": parts}

        if len(parts) >= 2 and parts[0] == "devices":
            result["type"] = "device"
            result["device_id"] = parts[1]
            if len(parts) >= 3:
                result["message_type"] = parts[2]

        elif len(parts) >= 2 and parts[0] == "groups":
            result["type"] = "group"
            result["group_id"] = parts[1]

        elif len(parts) >= 2 and parts[0] == "automation":
            result["type"] = "automation"
            result["automation_id"] = parts[1]

        return result
