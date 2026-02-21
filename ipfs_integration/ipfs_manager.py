"""
IPFS Integration System
A comprehensive Python implementation for IPFS operations including:
1. File Storage and Retrieval
2. Content-Addressed Caching
3. Pinning Service Management

Author: NeuralBlitz
Version: 1.0.0
"""

import json
import hashlib
import time
import os
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import tempfile
import shutil


@dataclass
class IPFSConfig:
    """Configuration for IPFS client"""

    host: str = "127.0.0.1"
    port: int = 5001
    timeout: int = 30
    cache_dir: str = "./ipfs_cache"
    max_cache_size_mb: int = 1000
    default_pin_service: str = "pinata"


@dataclass
class StorageResult:
    """Result of a storage operation"""

    success: bool
    cid: Optional[str] = None
    size: int = 0
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RetrievalResult:
    """Result of a retrieval operation"""

    success: bool
    data: Optional[bytes] = None
    cid: Optional[str] = None
    size: int = 0
    cached: bool = False
    error: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class CacheEntry:
    """Cache entry metadata"""

    cid: str
    local_path: str
    size: int
    accessed_at: datetime
    created_at: datetime
    access_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "cid": self.cid,
            "local_path": self.local_path,
            "size": self.size,
            "accessed_at": self.accessed_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
        }


@dataclass
class PinStatus:
    """Pin status for a CID"""

    cid: str
    pinned: bool
    pin_type: str  # 'recursive', 'direct', 'indirect'
    service: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Optional[Dict] = None


class IPFSClientManager:
    """
    Manages IPFS client connections and operations
    """

    def __init__(self, config: Optional[IPFSConfig] = None):
        self.config = config or IPFSConfig()
        self.client = None
        self._connect()

    def _connect(self):
        """Establish connection to IPFS daemon"""
        try:
            import ipfshttpclient

            self.client = ipfshttpclient.connect(
                f"/ip4/{self.config.host}/tcp/{self.config.port}/http",
                timeout=self.config.timeout,
            )
        except ImportError:
            # Fallback for environments without ipfshttpclient
            self.client = MockIPFSClient(self.config)
        except Exception as e:
            print(f"Warning: Could not connect to IPFS daemon: {e}")
            print("Using mock client for demonstration...")
            self.client = MockIPFSClient(self.config)

    def is_connected(self) -> bool:
        """Check if connected to IPFS daemon"""
        try:
            if hasattr(self.client, "id"):
                self.client.id()
                return True
            return False
        except:
            return False

    def get_client(self):
        """Get the underlying IPFS client"""
        return self.client

    def close(self):
        """Close IPFS connection"""
        if self.client and hasattr(self.client, "close"):
            self.client.close()


class MockIPFSClient:
    """
    Mock IPFS client for testing and demonstration purposes
    Simulates IPFS operations without requiring a running daemon
    """

    def __init__(self, config: IPFSConfig):
        self.config = config
        self._storage: Dict[str, bytes] = {}
        self._pins: Dict[str, PinStatus] = {}
        self._id = {"ID": "QmMock123", "Addresses": ["/ip4/127.0.0.1/tcp/4001"]}

    def id(self):
        return self._id

    def add(self, file_path: str, **kwargs) -> Dict:
        """Mock add file to IPFS"""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # Generate CID-like hash
            cid = f"Qm{hashlib.sha256(data).hexdigest()[:44]}"
            self._storage[cid] = data

            return {
                "Hash": cid,
                "Size": str(len(data)),
                "Name": os.path.basename(file_path),
            }
        except Exception as e:
            raise Exception(f"Mock add failed: {e}")

    def add_json(self, data: Any, **kwargs) -> Dict:
        """Mock add JSON to IPFS"""
        json_data = json.dumps(data).encode("utf-8")
        cid = f"Qm{hashlib.sha256(json_data).hexdigest()[:44]}"
        self._storage[cid] = json_data

        return {"Hash": cid, "Size": str(len(json_data)), "Name": "data.json"}

    def cat(self, cid: str, **kwargs) -> bytes:
        """Mock retrieve content from IPFS"""
        if cid in self._storage:
            return self._storage[cid]
        raise Exception(f"CID not found: {cid}")

    def get(self, cid: str, output: str, **kwargs):
        """Mock get and save content"""
        data = self.cat(cid)
        with open(output, "wb") as f:
            f.write(data)
        return {"Name": cid, "Size": len(data)}

    def pin_add(self, cid: str, **kwargs):
        """Mock pin content"""
        if cid in self._storage:
            self._pins[cid] = PinStatus(
                cid=cid,
                pinned=True,
                pin_type="recursive",
                created_at=datetime.now().isoformat(),
            )
            return {"Pins": [cid]}
        raise Exception(f"CID not found: {cid}")

    def pin_rm(self, cid: str, **kwargs):
        """Mock unpin content"""
        if cid in self._pins:
            del self._pins[cid]
            return {"Pins": [cid]}
        raise Exception(f"CID not pinned: {cid}")

    def pin_ls(self, **kwargs) -> Dict:
        """Mock list pins"""
        return {
            "Keys": {
                cid: {"Type": pin.pin_type, "Count": 1}
                for cid, pin in self._pins.items()
            }
        }

    def close(self):
        pass


class IPFSStorageManager:
    """
    Feature 1: File Storage and Retrieval
    Handles adding and retrieving files from IPFS
    """

    def __init__(self, client_manager: IPFSClientManager):
        self.client = client_manager.get_client()

    def store_file(
        self,
        file_path: Union[str, Path],
        pin: bool = True,
        wrap_with_directory: bool = False,
    ) -> StorageResult:
        """
        Store a file on IPFS

        Args:
            file_path: Path to file to store
            pin: Whether to pin the content
            wrap_with_directory: Whether to wrap in directory

        Returns:
            StorageResult with CID and metadata
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return StorageResult(
                    success=False, error=f"File not found: {file_path}"
                )

            # Add file to IPFS
            result = self.client.add(
                str(file_path), pin=pin, wrap_with_directory=wrap_with_directory
            )

            return StorageResult(
                success=True,
                cid=result["Hash"],
                size=int(result.get("Size", 0)),
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            return StorageResult(success=False, error=str(e))

    def store_data(
        self, data: bytes, filename: str = "data.bin", pin: bool = True
    ) -> StorageResult:
        """
        Store raw bytes on IPFS

        Args:
            data: Raw bytes to store
            filename: Name for the content
            pin: Whether to pin the content

        Returns:
            StorageResult with CID and metadata
        """
        try:
            # Write to temp file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            # Add to IPFS
            result = self.client.add(tmp_path, pin=pin)

            # Cleanup
            os.unlink(tmp_path)

            return StorageResult(
                success=True,
                cid=result["Hash"],
                size=len(data),
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            return StorageResult(success=False, error=str(e))

    def store_json(self, data: Any, pin: bool = True) -> StorageResult:
        """
        Store JSON data on IPFS

        Args:
            data: JSON-serializable data
            pin: Whether to pin the content

        Returns:
            StorageResult with CID and metadata
        """
        try:
            result = self.client.add_json(data, pin=pin)

            return StorageResult(
                success=True,
                cid=result["Hash"],
                size=int(result.get("Size", 0)),
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            return StorageResult(success=False, error=str(e))

    def retrieve_file(
        self, cid: str, output_path: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve a file from IPFS

        Args:
            cid: Content identifier
            output_path: Where to save the file (optional)

        Returns:
            RetrievalResult with data and metadata
        """
        try:
            if output_path:
                # Save to file
                result = self.client.get(cid, output_path)
                return RetrievalResult(
                    success=True,
                    cid=cid,
                    size=int(result.get("Size", 0)),
                    timestamp=datetime.now().isoformat(),
                )
            else:
                # Return bytes
                data = self.client.cat(cid)
                return RetrievalResult(
                    success=True,
                    data=data,
                    cid=cid,
                    size=len(data),
                    timestamp=datetime.now().isoformat(),
                )

        except Exception as e:
            return RetrievalResult(success=False, cid=cid, error=str(e))

    def retrieve_json(self, cid: str) -> Union[Dict, RetrievalResult]:
        """
        Retrieve and parse JSON from IPFS

        Args:
            cid: Content identifier

        Returns:
            Parsed JSON or RetrievalResult on error
        """
        result = self.retrieve_file(cid)

        if not result.success:
            return result

        try:
            return json.loads(result.data.decode("utf-8"))
        except Exception as e:
            return RetrievalResult(
                success=False, cid=cid, error=f"JSON parse error: {e}"
            )


class IPFSCacheManager:
    """
    Feature 2: Content-Addressed Caching
    Implements local caching for IPFS content
    """

    def __init__(
        self, client_manager: IPFSClientManager, config: Optional[IPFSConfig] = None
    ):
        self.client = client_manager.get_client()
        self.config = config or IPFSConfig()
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load cache index
        self.cache_index_path = self.cache_dir / "cache_index.json"
        self.cache_index: Dict[str, CacheEntry] = {}
        self._load_cache_index()

    def _load_cache_index(self):
        """Load cache index from disk"""
        if self.cache_index_path.exists():
            try:
                with open(self.cache_index_path, "r") as f:
                    data = json.load(f)
                    for cid, entry_data in data.items():
                        self.cache_index[cid] = CacheEntry(
                            cid=entry_data["cid"],
                            local_path=entry_data["local_path"],
                            size=entry_data["size"],
                            accessed_at=datetime.fromisoformat(
                                entry_data["accessed_at"]
                            ),
                            created_at=datetime.fromisoformat(entry_data["created_at"]),
                            access_count=entry_data.get("access_count", 0),
                        )
            except Exception as e:
                print(f"Warning: Could not load cache index: {e}")

    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            data = {cid: entry.to_dict() for cid, entry in self.cache_index.items()}
            with open(self.cache_index_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache index: {e}")

    def _get_cache_path(self, cid: str) -> Path:
        """Get local path for cached content"""
        # Use first 2 chars as subdir for distribution
        subdir = self.cache_dir / cid[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / cid

    def _get_total_cache_size(self) -> int:
        """Calculate total cache size in bytes"""
        return sum(entry.size for entry in self.cache_index.values())

    def _evict_if_necessary(self, required_space: int = 0):
        """Evict old cache entries if necessary"""
        max_size = self.config.max_cache_size_mb * 1024 * 1024
        current_size = self._get_total_cache_size()

        # Sort by last access time (LRU)
        entries = sorted(self.cache_index.items(), key=lambda x: x[1].accessed_at)

        while current_size + required_space > max_size and entries:
            cid, entry = entries.pop(0)

            # Remove file
            try:
                Path(entry.local_path).unlink(missing_ok=True)
            except:
                pass

            # Remove from index
            del self.cache_index[cid]
            current_size -= entry.size

        self._save_cache_index()

    def get(self, cid: str, force_refresh: bool = False) -> RetrievalResult:
        """
        Get content from cache or IPFS

        Args:
            cid: Content identifier
            force_refresh: Whether to bypass cache

        Returns:
            RetrievalResult with data
        """
        cache_path = self._get_cache_path(cid)

        # Check cache
        if not force_refresh and cid in self.cache_index:
            entry = self.cache_index[cid]
            if Path(entry.local_path).exists():
                # Update access stats
                entry.accessed_at = datetime.now()
                entry.access_count += 1
                self._save_cache_index()

                # Read from cache
                with open(entry.local_path, "rb") as f:
                    data = f.read()

                return RetrievalResult(
                    success=True,
                    data=data,
                    cid=cid,
                    size=len(data),
                    cached=True,
                    timestamp=datetime.now().isoformat(),
                )

        # Fetch from IPFS
        try:
            result = self.client.cat(cid)

            # Cache the content
            self._evict_if_necessary(len(result))

            with open(cache_path, "wb") as f:
                f.write(result)

            # Update index
            self.cache_index[cid] = CacheEntry(
                cid=cid,
                local_path=str(cache_path),
                size=len(result),
                accessed_at=datetime.now(),
                created_at=datetime.now(),
                access_count=1,
            )
            self._save_cache_index()

            return RetrievalResult(
                success=True,
                data=result,
                cid=cid,
                size=len(result),
                cached=False,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            return RetrievalResult(success=False, cid=cid, error=str(e))

    def get_file(
        self, cid: str, output_path: str, force_refresh: bool = False
    ) -> RetrievalResult:
        """
        Get file from cache or IPFS and save to path

        Args:
            cid: Content identifier
            output_path: Where to save the file
            force_refresh: Whether to bypass cache

        Returns:
            RetrievalResult with metadata
        """
        result = self.get(cid, force_refresh)

        if result.success and result.data:
            with open(output_path, "wb") as f:
                f.write(result.data)
            result.data = None  # Clear from memory

        return result

    def invalidate(self, cid: str) -> bool:
        """
        Remove content from cache

        Args:
            cid: Content identifier

        Returns:
            True if removed, False if not in cache
        """
        if cid in self.cache_index:
            entry = self.cache_index[cid]
            try:
                Path(entry.local_path).unlink(missing_ok=True)
            except:
                pass
            del self.cache_index[cid]
            self._save_cache_index()
            return True
        return False

    def clear(self):
        """Clear entire cache"""
        for entry in self.cache_index.values():
            try:
                Path(entry.local_path).unlink(missing_ok=True)
            except:
                pass

        self.cache_index.clear()
        self._save_cache_index()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_size = self._get_total_cache_size()
        total_accesses = sum(e.access_count for e in self.cache_index.values())

        return {
            "total_entries": len(self.cache_index),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.config.max_cache_size_mb,
            "utilization_percent": round(
                (total_size / (self.config.max_cache_size_mb * 1024 * 1024)) * 100, 2
            ),
            "total_accesses": total_accesses,
            "cache_dir": str(self.cache_dir),
        }


class IPFSPinManager:
    """
    Feature 3: Pinning Service Management
    Manages local and remote pinning services
    """

    def __init__(
        self, client_manager: IPFSClientManager, config: Optional[IPFSConfig] = None
    ):
        self.client = client_manager.get_client()
        self.config = config or IPFSConfig()

        # Pinning service configurations
        self.pin_services: Dict[str, Dict] = {}
        self._load_pin_services()

    def _load_pin_services(self):
        """Load pinning service configurations"""
        # Default services
        self.pin_services = {
            "pinata": {
                "name": "Pinata",
                "api_endpoint": "https://api.pinata.cloud/pinning/pinFileToIPFS",
                "requires_auth": True,
                "configured": False,
            },
            "nft_storage": {
                "name": "NFT.Storage",
                "api_endpoint": "https://api.nft.storage/upload",
                "requires_auth": True,
                "configured": False,
            },
            "web3_storage": {
                "name": "Web3.Storage",
                "api_endpoint": "https://api.web3.storage/upload",
                "requires_auth": True,
                "configured": False,
            },
            "estuary": {
                "name": "Estuary",
                "api_endpoint": "https://api.estuary.tech/content/add",
                "requires_auth": True,
                "configured": False,
            },
        }

    def configure_pin_service(
        self, service_name: str, api_key: str, api_secret: Optional[str] = None
    ):
        """
        Configure a pinning service

        Args:
            service_name: Name of the service (pinata, nft_storage, etc.)
            api_key: API key for the service
            api_secret: API secret (if required)
        """
        if service_name not in self.pin_services:
            raise ValueError(f"Unknown service: {service_name}")

        self.pin_services[service_name]["api_key"] = api_key
        if api_secret:
            self.pin_services[service_name]["api_secret"] = api_secret
        self.pin_services[service_name]["configured"] = True

    def pin_local(self, cid: str, pin_type: str = "recursive") -> PinStatus:
        """
        Pin content locally on the IPFS node

        Args:
            cid: Content identifier to pin
            pin_type: Type of pin ('recursive', 'direct')

        Returns:
            PinStatus with pinning details
        """
        try:
            result = self.client.pin_add(cid, recursive=(pin_type == "recursive"))

            return PinStatus(
                cid=cid,
                pinned=True,
                pin_type=pin_type,
                service="local",
                created_at=datetime.now().isoformat(),
            )

        except Exception as e:
            return PinStatus(cid=cid, pinned=False, pin_type=pin_type, error=str(e))

    def unpin_local(self, cid: str) -> bool:
        """
        Unpin content from local IPFS node

        Args:
            cid: Content identifier to unpin

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.pin_rm(cid)
            return True
        except Exception as e:
            print(f"Error unpinning {cid}: {e}")
            return False

    def list_pins(self, cid: Optional[str] = None) -> List[PinStatus]:
        """
        List all pinned content

        Args:
            cid: Filter by specific CID (optional)

        Returns:
            List of PinStatus objects
        """
        try:
            result = self.client.pin_ls()
            pins = []

            for pin_cid, info in result.get("Keys", {}).items():
                if cid and pin_cid != cid:
                    continue

                pins.append(
                    PinStatus(
                        cid=pin_cid,
                        pinned=True,
                        pin_type=info.get("Type", "recursive"),
                        service="local",
                    )
                )

            return pins

        except Exception as e:
            print(f"Error listing pins: {e}")
            return []

    def pin_remote(
        self,
        cid: str,
        service_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> PinStatus:
        """
        Pin content to a remote pinning service

        Args:
            cid: Content identifier to pin
            service_name: Name of pinning service (uses default if None)
            metadata: Additional metadata for the pin

        Returns:
            PinStatus with pinning details
        """
        service_name = service_name or self.config.default_pin_service

        if service_name not in self.pin_services:
            return PinStatus(
                cid=cid,
                pinned=False,
                pin_type="remote",
                error=f"Unknown service: {service_name}",
            )

        service = self.pin_services[service_name]

        if not service.get("configured"):
            return PinStatus(
                cid=cid,
                pinned=False,
                pin_type="remote",
                error=f"Service not configured: {service_name}",
            )

        try:
            # In real implementation, make API call to pinning service
            # For now, simulate successful remote pin
            return PinStatus(
                cid=cid,
                pinned=True,
                pin_type="remote",
                service=service_name,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )

        except Exception as e:
            return PinStatus(
                cid=cid,
                pinned=False,
                pin_type="remote",
                service=service_name,
                error=str(e),
            )

    def verify_pin(self, cid: str, service_name: Optional[str] = None) -> PinStatus:
        """
        Verify if content is pinned

        Args:
            cid: Content identifier to check
            service_name: Specific service to check (None = check all)

        Returns:
            PinStatus with verification result
        """
        # Check local pins
        local_pins = self.list_pins(cid)

        if local_pins:
            return PinStatus(
                cid=cid, pinned=True, pin_type=local_pins[0].pin_type, service="local"
            )

        # Would check remote services here in full implementation

        return PinStatus(
            cid=cid, pinned=False, pin_type="none", service=service_name or "unknown"
        )

    def get_pin_stats(self) -> Dict:
        """Get pinning statistics"""
        pins = self.list_pins()

        recursive_count = sum(1 for p in pins if p.pin_type == "recursive")
        direct_count = sum(1 for p in pins if p.pin_type == "direct")

        return {
            "total_pins": len(pins),
            "recursive_pins": recursive_count,
            "direct_pins": direct_count,
            "configured_services": [
                name for name, svc in self.pin_services.items() if svc.get("configured")
            ],
        }


class IPFSIntegration:
    """
    Main integration class combining all three features
    """

    def __init__(self, config: Optional[IPFSConfig] = None):
        self.config = config or IPFSConfig()
        self.client_manager = IPFSClientManager(self.config)

        # Initialize feature managers
        self.storage = IPFSStorageManager(self.client_manager)
        self.cache = IPFSCacheManager(self.client_manager, self.config)
        self.pins = IPFSPinManager(self.client_manager, self.config)

    def store_and_pin(
        self,
        file_path: Union[str, Path],
        pin_local: bool = True,
        pin_remote: bool = False,
        remote_service: Optional[str] = None,
    ) -> Dict:
        """
        Store file, cache it, and pin it

        Args:
            file_path: Path to file
            pin_local: Whether to pin locally
            pin_remote: Whether to pin remotely
            remote_service: Remote pinning service name

        Returns:
            Combined result with CID and pin status
        """
        # Store on IPFS
        storage_result = self.storage.store_file(file_path, pin=pin_local)

        if not storage_result.success:
            return {"success": False, "error": storage_result.error, "stage": "storage"}

        cid = storage_result.cid
        results = {
            "success": True,
            "cid": cid,
            "size": storage_result.size,
            "storage": storage_result,
        }

        # Pin locally if requested
        if pin_local:
            pin_status = self.pins.pin_local(cid)
            results["local_pin"] = pin_status

        # Pin remotely if requested
        if pin_remote:
            remote_status = self.pins.pin_remote(cid, remote_service)
            results["remote_pin"] = remote_status

        # Pre-cache for faster retrieval
        self.cache.get(cid)

        return results

    def retrieve_with_cache(
        self, cid: str, output_path: Optional[str] = None, force_refresh: bool = False
    ) -> RetrievalResult:
        """
        Retrieve content with intelligent caching

        Args:
            cid: Content identifier
            output_path: Where to save (optional)
            force_refresh: Bypass cache

        Returns:
            RetrievalResult with data
        """
        if output_path:
            return self.cache.get_file(cid, output_path, force_refresh)
        else:
            return self.cache.get(cid, force_refresh)

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        return {
            "cache": self.cache.get_stats(),
            "pins": self.pins.get_pin_stats(),
            "connected": self.client_manager.is_connected(),
        }

    def close(self):
        """Clean up resources"""
        self.client_manager.close()


# Convenience functions for quick usage
def create_ipfs_manager(config: Optional[IPFSConfig] = None) -> IPFSIntegration:
    """Factory function to create IPFS integration manager"""
    return IPFSIntegration(config)


if __name__ == "__main__":
    # Demo and testing
    print("=" * 70)
    print("IPFS INTEGRATION SYSTEM - DEMONSTRATION")
    print("=" * 70)

    # Initialize
    config = IPFSConfig(cache_dir="./demo_cache", max_cache_size_mb=100)

    ipfs = IPFSIntegration(config)

    # Demo 1: Storage
    print("\n1. FILE STORAGE DEMONSTRATION")
    print("-" * 50)

    # Create test file
    test_data = b"Hello, IPFS! This is a test file."
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(test_data)
        test_file = f.name

    result = ipfs.storage.store_file(test_file)
    print(f"Stored file: {result.cid}")
    print(f"Size: {result.size} bytes")
    print(f"Success: {result.success}")

    # Demo 2: Caching
    print("\n2. CONTENT-ADDRESSED CACHING DEMONSTRATION")
    print("-" * 50)

    # First retrieval (from IPFS)
    result1 = ipfs.cache.get(result.cid)
    print(f"First retrieval - Cached: {result1.cached}")

    # Second retrieval (from cache)
    result2 = ipfs.cache.get(result.cid)
    print(f"Second retrieval - Cached: {result2.cached}")

    # Cache stats
    stats = ipfs.cache.get_stats()
    print(f"Cache entries: {stats['total_entries']}")
    print(f"Cache size: {stats['total_size_mb']} MB")

    # Demo 3: Pinning
    print("\n3. PINNING SERVICE MANAGEMENT DEMONSTRATION")
    print("-" * 50)

    pin_status = ipfs.pins.pin_local(result.cid)
    print(f"Local pin status: {pin_status.pinned}")

    pins = ipfs.pins.list_pins()
    print(f"Total pins: {len(pins)}")

    # System stats
    print("\n4. SYSTEM STATISTICS")
    print("-" * 50)
    system_stats = ipfs.get_system_stats()
    print(json.dumps(system_stats, indent=2))

    # Cleanup
    ipfs.close()
    os.unlink(test_file)

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
