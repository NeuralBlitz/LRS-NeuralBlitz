"""
IPFS Integration System

A comprehensive Python implementation for IPFS operations including:
1. File Storage and Retrieval
2. Content-Addressed Caching
3. Pinning Service Management
"""

from .ipfs_manager import (
    IPFSIntegration,
    IPFSConfig,
    IPFSClientManager,
    IPFSStorageManager,
    IPFSCacheManager,
    IPFSPinManager,
    StorageResult,
    RetrievalResult,
    CacheEntry,
    PinStatus,
    create_ipfs_manager,
)

__version__ = "1.0.0"
__author__ = "NeuralBlitz"

__all__ = [
    "IPFSIntegration",
    "IPFSConfig",
    "IPFSClientManager",
    "IPFSStorageManager",
    "IPFSCacheManager",
    "IPFSPinManager",
    "StorageResult",
    "RetrievalResult",
    "CacheEntry",
    "PinStatus",
    "create_ipfs_manager",
]
