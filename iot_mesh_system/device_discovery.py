"""
IoT Device Mesh Integration System - Device Discovery Module
==========================================================
mDNS (Avahi/Zeroconf) and SSDP (Simple Service Discovery Protocol)
implementation for automatic device discovery.

Author: NeuralBlitz Systems
Version: 2.0.0
"""

import asyncio
import json
import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

# Try to import zeroconf, fall back to mock if not available
try:
    import zeroconf
    from zeroconf import ServiceBrowser, Zeroconf

    ZEROCONF_AVAILABLE = True
except ImportError:
    Zeroconf = None
    ServiceBrowser = None
    ZEROCONF_AVAILABLE = False

    # Mock zeroconf classes for type checking
    class Zeroconf:
        def __init__(self):
            pass

        def close(self):
            pass

    class ServiceBrowser:
        def __init__(self, *args, **kwargs):
            pass

        def cancel(self):
            pass


logger = logging.getLogger(__name__)


# Service types for IoT devices
class ServiceType(Enum):
    """Common IoT service types."""

    HTTP = "_http._tcp.local."
    MQTT = "_mqtt._tcp.local."
    HOMEKIT = "_hap._tcp.local."
    HOMEBRIDGE = "_hap._tcp."
    GOOGLE_HOME = "_googlecast._tcp.local."
    AMAZON_ECHO = "_amzn-ws._tcp.local."
    PHILIPS_HUE = "_hue._tcp.local."
    IKEA_TRADFRI = "_tradfri._tcp.local."
    LIFX = "_lifx._tcp.local."
    CUSTOM = "_iot._tcp.local."
    SSDP_ALL = "ssdp:all"
    UPNP_ROOT = "upnp:rootdevice"


@dataclass
class DiscoveredService:
    """Represents a discovered network service."""

    name: str
    service_type: ServiceType
    host: str
    port: int
    url: str = ""
    properties: Dict[str, str] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)
    protocol: str = ""  # "mdns" or "ssdp"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "service_type": self.service_type.value,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "properties": self.properties,
            "discovered_at": self.discovered_at.isoformat(),
            "protocol": self.protocol,
        }


class mDNSDiscovery:
    """
    mDNS/Zeroconf device discovery implementation.
    Uses zeroconf library for service discovery.
    """

    def __init__(
        self,
        service_types: List[ServiceType] = None,
        auto_terminate: bool = True,
        timeout: int = 30,
    ):
        self.service_types = service_types or [
            ServiceType.HTTP,
            ServiceType.MQTT,
            ServiceType.CUSTOM,
        ]
        self.auto_terminate = auto_terminate
        self.timeout = timeout

        self._zeroconf: Optional[zeroconf.Zeroconf] = None
        self._browsers: List[zeroconf.ServiceBrowser] = []
        self._discovered_services: Dict[str, DiscoveredService] = {}
        self._callbacks: List[Callable[[DiscoveredService], None]] = []
        self._running = False
        self._lock = threading.RLock()

        logger.info("mDNS Discovery initialized")

    def start(self):
        """Start mDNS discovery."""
        if self._running:
            return

        try:
            self._zeroconf = zeroconf.Zeroconf()
            self._running = True

            for service_type in self.service_types:
                browser = zeroconf.ServiceBrowser(
                    self._zeroconf,
                    service_type.value,
                    self._get_service_listener(service_type),
                )
                self._browsers.add(browser)

            logger.info(
                f"mDNS Discovery started for {len(self.service_types)} service types"
            )

            if self.auto_terminate:
                threading.Timer(self.timeout, self.stop).start()

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            self._running = False

    def stop(self):
        """Stop mDNS discovery."""
        if not self._running:
            return

        self._running = False

        try:
            for browser in self._browsers:
                browser.cancel()

            if self._zeroconf:
                self._zeroconf.close()
                self._zeroconf = None

            self._browsers.clear()
            logger.info("mDNS Discovery stopped")

        except Exception as e:
            logger.error(f"Error stopping mDNS discovery: {e}")

    def _get_service_listener(self, service_type: ServiceType):
        """Create a service listener for a specific service type."""

        class ServiceListener(zeroconf.ServiceListener):
            def __init__(inner_self):
                inner_self.service_type = service_type

            def add_service(inner_self, zc: zeroconf.Zeroconf, type_: str, name: str):
                info = zc.get_service_info(type_, name)
                if info:
                    service = self._parse_service_info(info, service_type, "mdns")
                    with self._lock:
                        self._discovered_services[service.name] = service
                    for callback in self._callbacks:
                        callback(service)
                    logger.info(
                        f"mDNS: Discovered {name} at {service.host}:{service.port}"
                    )

            def remove_service(
                inner_self, zc: zeroconf.Zeroconf, type_: str, name: str
            ):
                with self._lock:
                    if name in self._discovered_services:
                        del self._discovered_services[name]
                        logger.info(f"mDNS: Service removed {name}")

            def update_service(
                inner_self, zc: zeroconf.Zeroconf, type_: str, name: str
            ):
                info = zc.get_service_info(type_, name)
                if info:
                    service = self._parse_service_info(info, service_type, "mdns")
                    with self._lock:
                        self._discovered_services[service.name] = service
                    logger.debug(f"mDNS: Service updated {name}")

        return ServiceListener()

    def _parse_service_info(
        self, info: zeroconf.ServiceInfo, service_type: ServiceType, protocol: str
    ) -> DiscoveredService:
        """Parse zeroconf ServiceInfo into DiscoveredService."""
        properties = {}

        # Parse properties from TXT record
        if info.properties:
            for key, value in info.properties.items():
                try:
                    properties[key.decode("utf-8")] = value.decode("utf-8")
                except:
                    properties[key.decode("utf-8")] = str(value)

        # Build URL
        url = (
            f"http://{socket.inet_ntoa(info.addresses[0])}:{info.port}"
            if info.addresses
            else ""
        )

        return DiscoveredService(
            name=info.name,
            service_type=service_type,
            host=socket.inet_ntoa(info.addresses[0]) if info.addresses else "",
            port=info.port,
            url=url,
            properties=properties,
            protocol=protocol,
        )

    def add_discovery_callback(self, callback: Callable[[DiscoveredService], None]):
        """Add a callback for discovered services."""
        self._callbacks.append(callback)

    def get_discovered_services(self) -> List[DiscoveredService]:
        """Get all discovered services."""
        with self._lock:
            return list(self._discovered_services.values())

    def get_services_by_type(
        self, service_type: ServiceType
    ) -> List[DiscoveredService]:
        """Get services filtered by type."""
        with self._lock:
            return [
                s
                for s in self._discovered_services.values()
                if s.service_type == service_type
            ]


class SSDPDiscovery:
    """
    SSDP (Simple Service Discovery Protocol) discovery implementation.
    Used for discovering UPnP devices on the network.
    """

    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900

    # SSDP search templates
    SSDP_SEARCH = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: {addr}:{port}\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 3\r\n"
        "ST: {st}\r\n"
        "\r\n"
    )

    def __init__(
        self,
        service_types: List[ServiceType] = None,
        search_interval: int = 60,
        timeout: int = 10,
    ):
        self.service_types = service_types or [
            ServiceType.SSDP_ALL,
            ServiceType.UPNP_ROOT,
        ]
        self.search_interval = search_interval
        self.timeout = timeout

        self._socket: Optional[socket.socket] = None
        self._running = False
        self._discovered_services: Dict[str, DiscoveredService] = {}
        self._callbacks: List[Callable[[DiscoveredService], None]] = []
        self._lock = threading.RLock()
        self._search_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None

        logger.info("SSDP Discovery initialized")

    def start(self):
        """Start SSDP discovery."""
        if self._running:
            return

        try:
            # Create UDP socket for SSDP
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(self.timeout)

            # Bind to any interface
            self._socket.bind(("", 0))

            # Set multicast options
            self._socket.setsockopt(
                socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 4)
            )

            self._running = True

            # Start receive thread
            self._receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self._receive_thread.start()

            # Start periodic search
            self._search_thread = threading.Thread(
                target=self._search_loop, daemon=True
            )
            self._search_thread.start()

            # Initial search
            self._send_search()

            logger.info("SSDP Discovery started")

        except Exception as e:
            logger.error(f"Failed to start SSDP discovery: {e}")
            self._running = False

    def stop(self):
        """Stop SSDP discovery."""
        if not self._running:
            return

        self._running = False

        try:
            if self._socket:
                self._socket.close()
                self._socket = None

            logger.info("SSDP Discovery stopped")

        except Exception as e:
            logger.error(f"Error stopping SSDP discovery: {e}")

    def _send_search(self):
        """Send SSDP M-SEARCH discovery message."""
        if not self._socket:
            return

        try:
            for service_type in self.service_types:
                search_msg = self.SSDP_SEARCH.format(
                    addr=self.SSDP_ADDR, port=self.SSDP_PORT, st=service_type.value
                )
                self._socket.sendto(
                    search_msg.encode("utf-8"), (self.SSDP_ADDR, self.SSDP_PORT)
                )
                logger.debug(f"SSDP: Sent search for {service_type.value}")

        except Exception as e:
            logger.error(f"Error sending SSDP search: {e}")

    def _search_loop(self):
        """Periodic search loop."""
        while self._running:
            time.sleep(self.search_interval)
            if self._running:
                self._send_search()

    def _receive_loop(self):
        """Receive SSDP responses."""
        while self._running:
            try:
                if not self._socket:
                    break

                try:
                    data, addr = self._socket.recvfrom(4096)
                    self._parse_response(data.decode("utf-8", errors="ignore"), addr[0])
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"Error receiving SSDP response: {e}")

            except Exception as e:
                if self._running:
                    logger.error(f"Receive loop error: {e}")
                time.sleep(1)

    def _parse_response(self, response: str, source_ip: str):
        """Parse SSDP response and extract service info."""
        lines = response.split("\r\n")

        if not lines or not lines[0].startswith("HTTP/1.1 200"):
            return

        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().upper()] = value.strip()

        # Extract service information
        st = headers.get("ST", "")
        usn = headers.get("USN", "")
        location = headers.get("LOCATION", "")

        # Parse location URL
        host, port = "", 0
        if location:
            try:
                parsed = urlparse(location)
                host = parsed.hostname or source_ip
                port = parsed.port or 80
            except:
                host = source_ip
                port = 80

        # Extract properties from headers
        properties = {
            "server": headers.get("SERVER", ""),
            "cache_control": headers.get("CACHE-CONTROL", ""),
            "location": location,
            "usn": usn,
        }

        # Create service entry
        service = DiscoveredService(
            name=usn.split("::")[0] if "::" in usn else st,
            service_type=self._identify_service_type(st),
            host=host,
            port=port,
            url=location,
            properties=properties,
            protocol="ssdp",
        )

        # Add callback
        with self._lock:
            self._discovered_services[usn] = service

        for callback in self._callbacks:
            callback(service)

        logger.info(f"SSDP: Discovered {st} at {host}:{port}")

    def _identify_service_type(self, st: str) -> ServiceType:
        """Identify the service type from SSDP search target."""
        st_lower = st.lower()

        if "upnp:rootdevice" in st_lower:
            return ServiceType.UPNP_ROOT
        elif "ssdp:all" in st_lower:
            return ServiceType.SSDP_ALL
        else:
            return ServiceType.CUSTOM

    def add_discovery_callback(self, callback: Callable[[DiscoveredService], None]):
        """Add a callback for discovered services."""
        self._callbacks.append(callback)

    def get_discovered_services(self) -> List[DiscoveredService]:
        """Get all discovered services."""
        with self._lock:
            return list(self._discovered_services.values())

    def get_services_by_type(
        self, service_type: ServiceType
    ) -> List[DiscoveredService]:
        """Get services filtered by type."""
        with self._lock:
            return [
                s
                for s in self._discovered_services.values()
                if s.service_type == service_type
            ]


class DeviceDiscoveryManager:
    """
    Unified device discovery manager combining mDNS and SSDP.
    """

    def __init__(self):
        self._mdns: Optional[mDNSDiscovery] = None
        self._ssdp: Optional[SSDPDiscovery] = None
        self._discovered_devices: Dict[str, DiscoveredService] = {}
        self._callbacks: List[Callable[[DiscoveredService], None]] = []
        self._lock = threading.RLock()

        logger.info("Device Discovery Manager initialized")

    def start(
        self,
        use_mdns: bool = True,
        use_ssdp: bool = True,
        mdns_service_types: List[ServiceType] = None,
        ssdp_service_types: List[ServiceType] = None,
    ):
        """Start device discovery."""

        if use_mdns:
            self._mdns = mDNSDiscovery(
                service_types=mdns_service_types, auto_terminate=False
            )
            self._mdns.add_discovery_callback(self._on_service_discovered)
            self._mdns.start()

        if use_ssdp:
            self._ssdp = SSDPDiscovery(service_types=ssdp_service_types)
            self._ssdp.add_discovery_callback(self._on_service_discovered)
            self._ssdp.start()

        logger.info("Device Discovery Manager started")

    def stop(self):
        """Stop device discovery."""
        if self._mdns:
            self._mdns.stop()
            self._mdns = None

        if self._ssdp:
            self._ssdp.stop()
            self._ssdp = None

        logger.info("Device Discovery Manager stopped")

    def _on_service_discovered(self, service: DiscoveredService):
        """Handle discovered service."""
        with self._lock:
            key = f"{service.protocol}:{service.name}"
            self._discovered_devices[key] = service

        for callback in self._callbacks:
            callback(service)

    def add_discovery_callback(self, callback: Callable[[DiscoveredService], None]):
        """Add a callback for discovered services."""
        self._callbacks.append(callback)

    def get_all_devices(self) -> List[DiscoveredService]:
        """Get all discovered devices."""
        with self._lock:
            return list(self._discovered_devices.values())

    def get_devices_by_protocol(self, protocol: str) -> List[DiscoveredService]:
        """Get devices filtered by protocol."""
        with self._lock:
            return [
                d for d in self._discovered_devices.values() if d.protocol == protocol
            ]

    def get_device_by_name(self, name: str) -> Optional[DiscoveredService]:
        """Get a device by name."""
        with self._lock:
            for device in self._discovered_devices.values():
                if device.name == name:
                    return device
        return None

    def force_discovery(self):
        """Force a new discovery cycle."""
        if self._mdns:
            self._mdns.stop()
            self._mdns.start()

        if self._ssdp:
            self._ssdp._send_search()


class NetworkScanner:
    """
    Network scanner for IP-based device discovery.
    """

    def __init__(self, subnet: str = None):
        self.subnet = subnet or self._get_default_subnet()
        self._discovered_hosts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        logger.info(f"Network Scanner initialized for {self.subnet}")

    def _get_default_subnet(self) -> str:
        """Get the default subnet from network interfaces."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            # Get subnet (assume /24)
            parts = ip.split(".")
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except:
            return "192.168.1.0/24"

    def scan_network(self, common_ports: List[int] = None) -> List[Dict[str, Any]]:
        """Scan the network for active hosts."""
        common_ports = common_ports or [80, 443, 1883, 8080, 8883, 5353]

        subnet_prefix = self.subnet.split("/")[0]
        base_ip = ".".join(subnet_prefix.split(".")[:-1])

        hosts = []

        def check_port(host: str, port: int) -> Optional[Dict[str, Any]]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    return {"host": host, "port": port, "open": True}
            except:
                pass
            return None

        logger.info(f"Scanning network {self.subnet}...")

        for i in range(1, 255):
            host = f"{base_ip}.{i}"

            # Check common ports in parallel
            for port in common_ports:
                result = check_port(host, port)
                if result:
                    with self._lock:
                        self._discovered_hosts[host] = result
                    hosts.append(result)

        logger.info(f"Network scan complete: {len(hosts)} hosts found")
        return hosts

    def get_discovered_hosts(self) -> List[Dict[str, Any]]:
        """Get all discovered hosts."""
        with self._lock:
            return list(self._discovered_hosts.values())

    def ping_host(self, host: str) -> bool:
        """Ping a host to check if it's alive."""
        try:
            import subprocess

            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host], capture_output=True, timeout=2
            )
            return result.returncode == 0
        except:
            return False
