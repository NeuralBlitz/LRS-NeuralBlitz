"""
NeuralBlitz Blockchain Integration Module
=========================================
Comprehensive Python implementation for:
1. Ethereum smart contract deployment and interaction (web3.py)
2. Hyperledger Fabric network connection (fabric SDK)
3. Decentralized identity (DID) management

Author: NeuralBlitz Architecture Team
Date: 2026-02-18
"""

import os
import json
import hashlib
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import threading

# Ethereum dependencies
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from web3.gas_strategies import linear
    from eth_account import Account
    from eth_abi import encode
    from eth_utils import to_checksum_address

    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logging.warning("web3.py not installed")

# Hyperledger Fabric dependencies
try:
    from hfc.fabric import Client
    from hfc.fabric.network import Network
    from hfc.fabric.channel import Channel

    FABRIC_SDK_AVAILABLE = True
except ImportError:
    FABRIC_SDK_AVAILABLE = False
    logging.warning("hfc not installed")

# DID dependencies
try:
    from did_resolver import Resolver
    from did_jwt import verify_jwt, JWT

    DID_AVAILABLE = True
except ImportError:
    DID_AVAILABLE = False
    logging.warning("DID libraries not installed")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Section 1: Ethereum Smart Contract Integration
# =============================================================================


class EthereumNetwork(Enum):
    """Ethereum network types"""

    MAINNET = 1
    GOERLI = 5
    SEPOLIA = 11155111
    POLYGON = 137
    POLYGON_MUMBAI = 80001
    BSC = 56
    LOCAL = 1337


@dataclass
class ContractDeploymentConfig:
    """Configuration for smart contract deployment"""

    network: EthereumNetwork
    provider_url: str
    private_key: str
    gas_price_gwei: int = 50
    confirmations: int = 2


@dataclass
class EthereumAsset:
    """Asset data from Ethereum contract"""

    token_id: int
    asset_type: str
    fabric_record_hash: str
    did_reference: str
    owner: str
    created_at: int
    updated_at: int
    is_active: bool


class ContractABI:
    """Smart contract ABI storage and management"""

    # Asset Registry Contract ABI (ERC-721 based)
    ASSET_REGISTRY_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "string", "name": "assetType", "type": "string"},
                {
                    "internalType": "bytes32",
                    "name": "fabricRecordHash",
                    "type": "bytes32",
                },
                {"internalType": "bytes32", "name": "didReference", "type": "bytes32"},
                {"internalType": "string[]", "name": "attrKeys", "type": "string[]"},
                {"internalType": "string[]", "name": "attrValues", "type": "string[]"},
            ],
            "name": "mintAsset",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
            ],
            "name": "ownerOf",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
            ],
            "name": "assets",
            "outputs": [
                {"internalType": "string", "name": "assetType"},
                {"internalType": "bytes32", "name": "fabricRecordHash"},
                {"internalType": "bytes32", "name": "didReference"},
                {"internalType": "uint256", "name": "createdAt"},
                {"internalType": "uint256", "name": "updatedAt"},
                {"internalType": "bool", "name": "isActive"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
                {"internalType": "bytes32", "name": "fabricTxHash", "type": "bytes32"},
                {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                {"internalType": "bytes", "name": "signature", "type": "bytes"},
            ],
            "name": "addCrossChainProof",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
                {
                    "internalType": "bytes32",
                    "name": "fabricStateHash",
                    "type": "bytes32",
                },
            ],
            "name": "verifyCrossChainOwnership",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {
                    "indexed": True,
                    "internalType": "bytes32",
                    "name": "fabricRecordHash",
                    "type": "bytes32",
                },
                {
                    "indexed": False,
                    "internalType": "bytes32",
                    "name": "didReference",
                    "type": "bytes32",
                },
                {
                    "indexed": False,
                    "internalType": "address",
                    "name": "owner",
                    "type": "address",
                },
            ],
            "name": "AssetMinted",
            "type": "event",
        },
    ]

    # DID Registry Contract ABI
    DID_REGISTRY_ABI = [
        {
            "inputs": [
                {"internalType": "bytes32", "name": "did", "type": "bytes32"},
                {"internalType": "bytes32", "name": "publicKeyHash", "type": "bytes32"},
                {
                    "internalType": "string",
                    "name": "serviceEndpoints",
                    "type": "string",
                },
            ],
            "name": "createDID",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "bytes32",
                    "name": "credentialHash",
                    "type": "bytes32",
                },
                {"internalType": "bytes32", "name": "subjectDID", "type": "bytes32"},
                {"internalType": "uint256", "name": "expiresAt", "type": "uint256"},
                {"internalType": "bytes32", "name": "fabricAnchor", "type": "bytes32"},
            ],
            "name": "issueCredential",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "bytes32",
                    "name": "credentialHash",
                    "type": "bytes32",
                },
                {"internalType": "bytes32", "name": "subjectDID", "type": "bytes32"},
            ],
            "name": "verifyCredential",
            "outputs": [
                {"internalType": "bool", "name": "isValid", "type": "bool"},
                {"internalType": "string", "name": "reason", "type": "string"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "credentialHash", "type": "bytes32"}
            ],
            "name": "revokeCredential",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "bytes32", "name": "did", "type": "bytes32"}],
            "name": "didDocuments",
            "outputs": [
                {"internalType": "address", "name": "controller", "type": "address"},
                {"internalType": "bytes32", "name": "publicKeyHash", "type": "bytes32"},
                {
                    "internalType": "string",
                    "name": "serviceEndpoints",
                    "type": "string",
                },
                {"internalType": "uint256", "name": "created", "type": "uint256"},
                {"internalType": "uint256", "name": "updated", "type": "uint256"},
                {"internalType": "bool", "name": "active", "type": "bool"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
    ]


class EthereumIntegration:
    """
    Ethereum blockchain integration for NeuralBlitz

    Provides:
    - Smart contract deployment
    - Asset minting and management
    - DID creation and credential management
    - Cross-chain proof verification
    """

    def __init__(
        self,
        provider_url: str,
        asset_registry_address: Optional[str] = None,
        did_registry_address: Optional[str] = None,
        private_key: Optional[str] = None,
        network: EthereumNetwork = EthereumNetwork.SEPOLIA,
    ):
        """
        Initialize Ethereum integration

        Args:
            provider_url: Ethereum node URL
            asset_registry_address: Asset registry contract address
            did_registry_address: DID registry contract address
            private_key: Private key for signing transactions
            network: Ethereum network type
        """
        if not WEB3_AVAILABLE:
            raise ImportError(
                "web3.py is required. Install: pip install web3 eth-account eth-abi"
            )

        self.provider_url = provider_url
        self.network = network
        self.w3 = Web3(Web3.HTTPProvider(provider_url))

        # Add middleware for POA chains
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {provider_url}")

        logger.info(f"Connected to Ethereum. Chain ID: {self.w3.eth.chain_id}")

        # Initialize contracts
        self.asset_registry = None
        self.did_registry = None

        if asset_registry_address:
            self.asset_registry = self.w3.eth.contract(
                address=to_checksum_address(asset_registry_address),
                abi=ContractABI.ASSET_REGISTRY_ABI,
            )

        if did_registry_address:
            self.did_registry = self.w3.eth.contract(
                address=to_checksum_address(did_registry_address),
                abi=ContractABI.DID_REGISTRY_ABI,
            )

        # Set up account
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Account loaded: {self.account.address}")

    # -------------------------------------------------------------------------
    # Contract Deployment
    # -------------------------------------------------------------------------

    def deploy_asset_registry(self, private_key: str) -> Tuple[str, str]:
        """
        Deploy asset registry contract

        Args:
            private_key: Deployer private key

        Returns:
            Tuple of (contract_address, transaction_hash)
        """
        account = Account.from_key(private_key)

        # Compile contract (would require solc in production)
        # For demo, return mock addresses
        logger.info("Deploying Asset Registry contract...")

        # In production, use web3.eth.contract() with bytecode
        # Here we return mock addresses for demonstration
        mock_address = to_checksum_address(
            "0x" + hashlib.sha256(b"AssetRegistry").hexdigest()[:40]
        )

        self.asset_registry = self.w3.eth.contract(
            address=mock_address, abi=ContractABI.ASSET_REGISTRY_ABI
        )

        return mock_address, "0x" + "00" * 32

    def deploy_did_registry(self, private_key: str) -> Tuple[str, str]:
        """
        Deploy DID registry contract

        Args:
            private_key: Deployer private key

        Returns:
            Tuple of (contract_address, transaction_hash)
        """
        logger.info("Deploying DID Registry contract...")

        mock_address = to_checksum_address(
            "0x" + hashlib.sha256(b"DIDRegistry").hexdigest()[:40]
        )

        self.did_registry = self.w3.eth.contract(
            address=mock_address, abi=ContractABI.DID_REGISTRY_ABI
        )

        return mock_address, "0x" + "00" * 32

    # -------------------------------------------------------------------------
    # Asset Management
    # -------------------------------------------------------------------------

    def mint_asset(
        self,
        to_address: str,
        asset_type: str,
        fabric_record_hash: str,
        did_reference: str,
        attributes: Optional[Dict[str, str]] = None,
        gas_price_gwei: int = 50,
    ) -> Dict[str, Any]:
        """
        Mint a new asset NFT with cross-chain reference

        Args:
            to_address: Recipient address
            asset_type: Type of asset
            fabric_record_hash: Hash from Fabric
            did_reference: DID reference
            attributes: Optional asset attributes
            gas_price_gwei: Gas price in Gwei

        Returns:
            Transaction receipt and token ID
        """
        if not self.account:
            raise ValueError("Private key required for minting")

        if not self.asset_registry:
            raise ValueError("Asset registry not initialized")

        # Prepare attributes
        attr_keys = list(attributes.keys()) if attributes else []
        attr_values = list(attributes.values()) if attributes else []

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.to_wei(gas_price_gwei, "gwei")

        txn = self.asset_registry.functions.mintAsset(
            to_checksum_address(to_address),
            asset_type,
            fabric_record_hash,
            did_reference,
            attr_keys,
            attr_values,
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": gas_price,
                "chainId": self.w3.eth.chain_id,
            }
        )

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Extract token ID from logs
        token_id = 0
        if receipt["logs"]:
            try:
                # Parse AssetMinted event
                event = self.asset_registry.events.AssetMinted().process_receipt(
                    receipt
                )
                if event:
                    token_id = event[0]["args"]["tokenId"]
            except Exception as e:
                logger.warning(f"Could not parse event: {e}")

        return {
            "transaction_hash": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "status": receipt["status"],
            "token_id": token_id,
            "gas_used": receipt["gasUsed"],
        }

    def get_asset(self, token_id: int) -> Optional[EthereumAsset]:
        """
        Retrieve asset data by token ID

        Args:
            token_id: NFT token ID

        Returns:
            EthereumAsset object or None
        """
        if not self.asset_registry:
            return None

        try:
            data = self.asset_registry.functions.assets(token_id).call()
            owner = self.asset_registry.functions.ownerOf(token_id).call()

            return EthereumAsset(
                token_id=token_id,
                asset_type=data[0],
                fabric_record_hash=data[1].hex(),
                did_reference=data[2].hex(),
                owner=owner,
                created_at=data[3],
                updated_at=data[4],
                is_active=data[5],
            )
        except Exception as e:
            logger.error(f"Error getting asset: {e}")
            return None

    def add_cross_chain_proof(
        self,
        token_id: int,
        fabric_tx_hash: str,
        merkle_root: str,
        signature: str,
        gas_price_gwei: int = 50,
    ) -> Dict[str, Any]:
        """
        Add cross-chain proof from Fabric

        Args:
            token_id: Token ID
            fabric_tx_hash: Fabric transaction hash
            merkle_root: Merkle root
            signature: ECDSA signature
            gas_price_gwei: Gas price

        Returns:
            Transaction receipt
        """
        if not self.account:
            raise ValueError("Private key required")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.to_wei(gas_price_gwei, "gwei")

        txn = self.asset_registry.functions.addCrossChainProof(
            token_id, fabric_tx_hash, merkle_root, signature
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": gas_price,
                "chainId": self.w3.eth.chain_id,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(txn, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "transaction_hash": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "status": receipt["status"],
        }

    def verify_cross_chain_ownership(
        self, token_id: int, fabric_state_hash: str
    ) -> bool:
        """Verify ownership against Fabric state"""
        if not self.asset_registry:
            return False

        return self.asset_registry.functions.verifyCrossChainOwnership(
            token_id, fabric_state_hash
        ).call()

    # -------------------------------------------------------------------------
    # DID Management
    # -------------------------------------------------------------------------

    def create_did(
        self,
        did: str,
        public_key_hash: str,
        service_endpoints: str,
        gas_price_gwei: int = 50,
    ) -> Dict[str, Any]:
        """
        Create a new DID

        Args:
            did: DID identifier
            public_key_hash: Hash of public key
            service_endpoints: JSON string of services
            gas_price_gwei: Gas price

        Returns:
            Transaction receipt
        """
        if not self.account:
            raise ValueError("Private key required")

        if not self.did_registry:
            raise ValueError("DID registry not initialized")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.to_wei(gas_price_gwei, "gwei")

        # Convert DID to bytes32
        did_bytes = bytes.fromhex(did.replace("0x", "").zfill(64)[:64])

        txn = self.did_registry.functions.createDID(
            did_bytes, public_key_hash, service_endpoints
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": gas_price,
                "chainId": self.w3.eth.chain_id,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(txn, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "transaction_hash": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "status": receipt["status"],
        }

    def issue_credential(
        self,
        credential_hash: str,
        subject_did: str,
        expires_at: int,
        fabric_anchor: str,
        gas_price_gwei: int = 50,
    ) -> Dict[str, Any]:
        """
        Issue verifiable credential

        Args:
            credential_hash: Hash of credential
            subject_did: Subject DID
            expires_at: Expiration timestamp
            fabric_anchor: Fabric anchor hash
            gas_price_gwei: Gas price

        Returns:
            Transaction receipt
        """
        if not self.account:
            raise ValueError("Private key required")

        nonce = self.w3.eth.get_transaction_count(self.account.address)

        txn = self.did_registry.functions.issueCredential(
            credential_hash, subject_did, expires_at, fabric_anchor
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": self.w3.to_wei(gas_price_gwei, "gwei"),
                "chainId": self.w3.eth.chain_id,
            }
        )

        signed_txn = self.w3.eth.account.sign_transaction(txn, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {"transaction_hash": tx_hash.hex(), "status": receipt["status"]}

    def verify_credential(
        self, credential_hash: str, subject_did: str
    ) -> Tuple[bool, str]:
        """
        Verify credential validity

        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.did_registry:
            return False, "Registry not initialized"

        result = self.did_registry.functions.verifyCredential(
            credential_hash, subject_did
        ).call()

        return result[0], result[1]

    # -------------------------------------------------------------------------
    # Utility Functions
    # -------------------------------------------------------------------------

    def generate_merkle_root(self, data: Dict) -> str:
        """Generate merkle root hash for Fabric anchoring"""
        data_json = json.dumps(data, sort_keys=True)
        return "0x" + hashlib.sha256(data_json.encode()).hexdigest()

    def generate_cross_chain_signature(
        self, token_id: int, fabric_tx_hash: str, merkle_root: str
    ) -> str:
        """Generate ECDSA signature for cross-chain proof"""
        if not self.account:
            raise ValueError("Private key required")

        message = encode(
            ["uint256", "bytes32", "bytes32"], [token_id, fabric_tx_hash, merkle_root]
        )

        signed = self.account.sign_message(message)
        return signed.signature.hex()

    def get_balance(self, address: str) -> float:
        """Get ETH balance"""
        return self.w3.eth.get_balance(to_checksum_address(address))


# =============================================================================
# Section 2: Hyperledger Fabric Integration
# =============================================================================


@dataclass
class FabricAsset:
    """Asset data from Fabric"""

    id: str
    asset_type: str
    owner: str
    value: float
    ethereum_token_id: str
    did: str
    created_at: str
    updated_at: str
    status: str
    merkle_root: str


class FabricIntegration:
    """
    Hyperledger Fabric blockchain integration for NeuralBlitz

    Provides:
    - Chaincode deployment and invocation
    - Asset management with private data
    - Cross-chain synchronization with Ethereum
    - DID-based access control
    """

    def __init__(
        self,
        network_config: Dict,
        org_name: str = "Org1",
        user_name: str = "Admin",
        channel_name: str = "neuralblitz",
        chaincode_name: str = "assetcc",
        chaincode_path: Optional[str] = None,
    ):
        """
        Initialize Fabric integration

        Args:
            network_config: Network connection profile
            org_name: Organization name
            user_name: User identity
            channel_name: Channel name
            chaincode_name: Chaincode name
            chaincode_path: Path to chaincode (Go)
        """
        if not FABRIC_SDK_AVAILABLE:
            raise ImportError("hfc is required. Install: pip install hfc")

        self.org_name = org_name
        self.user_name = user_name
        self.channel_name = channel_name
        self.chaincode_name = chaincode_name
        self.chaincode_path = chaincode_path

        # Initialize Fabric client
        self.client = Client(net_profile=json.dumps(network_config))
        self.org_admin = None
        self.channel = None

        # Will be initialized on first use
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization"""
        if self._initialized:
            return

        # Get admin user
        self.org_admin = self.client.get_user(
            org_name=self.org_name, username=self.user_name
        )

        # Get channel
        self.channel = self.client.get_channel(self.channel_name)

        self._initialized = True
        logger.info(f"Fabric client initialized for {self.org_name}/{self.user_name}")

    # -------------------------------------------------------------------------
    # Chaincode Management
    # -------------------------------------------------------------------------

    def install_chaincode(
        self, version: str = "1.0", language: str = "golang"
    ) -> Dict[str, Any]:
        """
        Install chaincode on peers

        Args:
            version: Chaincode version
            language: Chaincode language

        Returns:
            Installation result
        """
        self._ensure_initialized()

        logger.info(f"Installing chaincode {self.chaincode_name} v{version}")

        # In production, use client.send_install_proposal()
        return {
            "success": True,
            "chaincode_name": self.chaincode_name,
            "version": version,
            "language": language,
        }

    def approve_chaincode(
        self, version: str = "1.0", sequence: int = 1, package_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve chaincode definition

        Args:
            version: Chaincode version
            sequence: Package sequence
            package_id: Package ID

        Returns:
            Approval result
        """
        self._ensure_initialized()

        logger.info(f"Approving chaincode {self.chaincode_name}")

        return {
            "success": True,
            "chaincode_name": self.chaincode_name,
            "version": version,
            "sequence": sequence,
        }

    def commit_chaincode(
        self, version: str = "1.0", sequence: int = 1
    ) -> Dict[str, Any]:
        """
        Commit chaincode definition

        Args:
            version: Chaincode version
            sequence: Package sequence

        Returns:
            Commit result
        """
        self._ensure_initialized()

        logger.info(f"Committing chaincode {self.chaincode_name}")

        return {"success": True, "transaction_id": f"tx-{datetime.now().timestamp()}"}

    # -------------------------------------------------------------------------
    # Asset Operations
    # -------------------------------------------------------------------------

    async def create_asset(
        self,
        asset_id: str,
        asset_type: str,
        owner: str,
        value: float,
        ethereum_token_id: str,
        did: str,
        confidential_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Create new asset on Fabric

        Args:
            asset_id: Unique identifier
            asset_type: Asset type
            owner: Owner MSP ID
            value: Asset value
            ethereum_token_id: Ethereum token ID
            did: Owner DID
            confidential_data: Private data

        Returns:
            Creation result
        """
        self._ensure_initialized()

        # Generate merkle root
        asset_data = {
            "id": asset_id,
            "type": asset_type,
            "owner": owner,
            "value": value,
            "ethereum_token_id": ethereum_token_id,
            "did": did,
            "timestamp": datetime.utcnow().isoformat(),
        }
        merkle_root = self._generate_merkle_root(asset_data)

        # Prepare transient data
        transient_map = {}
        if confidential_data:
            transient_map["privateData"] = json.dumps(confidential_data).encode()

        # In production, invoke chaincode
        # For demo, return mock response
        return {
            "success": True,
            "transaction_id": f"tx-{asset_id}-{datetime.now().timestamp()}",
            "asset_id": asset_id,
            "merkle_root": merkle_root,
            "ethereum_token_id": ethereum_token_id,
        }

    async def read_asset(self, asset_id: str) -> Optional[FabricAsset]:
        """
        Read asset from ledger

        Args:
            asset_id: Asset ID

        Returns:
            FabricAsset or None
        """
        self._ensure_initialized()

        # In production, query chaincode
        # Return mock for demo
        return FabricAsset(
            id=asset_id,
            asset_type="Property",
            owner=f"{self.org_name}MSP",
            value=500000.0,
            ethereum_token_id="1",
            did="did:ethr:0x123",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            status="ACTIVE",
            merkle_root=self._generate_merkle_root({"id": asset_id}),
        )

    async def update_asset(
        self, asset_id: str, new_value: float, new_status: str
    ) -> Dict[str, Any]:
        """
        Update asset

        Args:
            asset_id: Asset ID
            new_value: New value
            new_status: New status

        Returns:
            Update result
        """
        self._ensure_initialized()

        return {
            "success": True,
            "transaction_id": f"tx-update-{asset_id}-{datetime.now().timestamp()}",
        }

    async def get_asset_history(self, asset_id: str) -> List[Dict]:
        """
        Get asset transaction history

        Args:
            asset_id: Asset ID

        Returns:
            List of history records
        """
        self._ensure_initialized()

        # Return mock history
        return [
            {
                "tx_id": f"tx-history-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "action": "CREATE" if i == 0 else "UPDATE",
                "actor": f"{self.org_name}MSP",
            }
            for i in range(3)
        ]

    async def get_all_assets(self) -> List[FabricAsset]:
        """Get all assets"""
        self._ensure_initialized()

        return [
            FabricAsset(
                id=f"asset-{i}",
                asset_type="Property",
                owner=f"{self.org_name}MSP",
                value=100000.0 * i,
                ethereum_token_id=str(i),
                did=f"did:ethr:0x{i:064x}",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                status="ACTIVE",
                merkle_root=self._generate_merkle_root({"id": f"asset-{i}"}),
            )
            for i in range(5)
        ]

    # -------------------------------------------------------------------------
    # Cross-Chain Operations
    # -------------------------------------------------------------------------

    async def verify_ethereum_ownership(
        self, asset_id: str, ethereum_address: str
    ) -> bool:
        """
        Verify ownership against Ethereum

        Args:
            asset_id: Asset ID
            ethereum_address: Ethereum address

        Returns:
            True if verified
        """
        asset = await self.read_asset(asset_id)
        if not asset:
            return False

        # In production, call Ethereum contract
        return asset.ethereum_token_id != "0"

    async def sync_to_ethereum(
        self, asset_id: str, ethereum_bridge: "EthereumIntegration"
    ) -> Dict[str, Any]:
        """
        Synchronize asset to Ethereum

        Args:
            asset_id: Asset ID
            ethereum_bridge: Ethereum bridge instance

        Returns:
            Sync result
        """
        asset = await self.read_asset(asset_id)
        if not asset:
            return {"success": False, "error": "Asset not found"}

        # Mint on Ethereum
        tx_result = ethereum_bridge.mint_asset(
            to_address=asset.owner,  # Would need proper ETH address
            asset_type=asset.asset_type,
            fabric_record_hash=asset.merkle_root,
            did_reference=asset.did,
            attributes={"fabric_id": asset.id},
        )

        return {
            "success": True,
            "ethereum_tx": tx_result["transaction_hash"],
            "token_id": tx_result["token_id"],
        }

    # -------------------------------------------------------------------------
    # Utility Functions
    # -------------------------------------------------------------------------

    def _generate_merkle_root(self, data: Dict) -> str:
        """Generate merkle root hash"""
        data_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_json.encode()).hexdigest()

    def get_channel_info(self) -> Dict[str, Any]:
        """Get channel information"""
        self._ensure_initialized()

        return {
            "name": self.channel_name,
            "org": self.org_name,
            "chaincode": self.chaincode_name,
        }


# =============================================================================
# Section 3: Decentralized Identity (DID) Management
# =============================================================================


@dataclass
class VerifiableCredential:
    """Verifiable Credential structure"""

    id: str
    issuer: str
    subject: str
    credential_type: List[str]
    claims: Dict
    issued_at: datetime
    expires_at: Optional[datetime]
    proof: Optional[Dict]


@dataclass
class DIDDocument:
    """W3C DID Document"""

    id: str
    controller: List[str]
    public_keys: List[Dict]
    services: List[Dict]
    created: datetime
    updated: datetime
    proof: Optional[Dict]


class DIDMethod(Enum):
    """Supported DID methods"""

    ETHR = "ethr"
    WEB = "web"
    KEY = "key"
    FABRIC = "fabric"


class DIDManager:
    """
    Decentralized Identity Manager for NeuralBlitz

    Provides:
    - DID creation and resolution
    - Verifiable credential issuance and verification
    - Cross-platform identity management
    - Integration with Ethereum and Fabric
    """

    def __init__(
        self,
        method: DIDMethod = DIDMethod.ETHR,
        ethereum_integration: Optional[EthereumIntegration] = None,
        fabric_integration: Optional[FabricIntegration] = None,
    ):
        """
        Initialize DID Manager

        Args:
            method: Primary DID method
            ethereum_integration: Ethereum integration instance
            fabric_integration: Fabric integration instance
        """
        self.method = method
        self.ethereum = ethereum_integration
        self.fabric = fabric_integration

        # In-memory DID storage (production would use proper registry)
        self._did_storage: Dict[str, DIDDocument] = {}
        self._credential_storage: Dict[str, VerifiableCredential] = {}

        logger.info(f"DID Manager initialized with method: {method.value}")

    # -------------------------------------------------------------------------
    # DID Operations
    # -------------------------------------------------------------------------

    def create_did(
        self,
        controller: str,
        public_keys: Optional[List[Dict]] = None,
        services: Optional[List[Dict]] = None,
    ) -> str:
        """
        Create new DID

        Args:
            controller: Controller address
            public_keys: Public keys
            services: Service endpoints

        Returns:
            DID string
        """
        # Generate DID based on method
        if self.method == DIDMethod.ETHR:
            # Use Ethereum address
            did = f"did:ethr:{controller}"
        elif self.method == DIDMethod.KEY:
            # Generate from public key
            key_hash = hashlib.sha256(controller.encode()).hexdigest()[:44]
            did = f"did:key:{key_hash}"
        else:
            # Generic
            unique_id = hashlib.sha256(
                f"{controller}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            did = f"did:{self.method.value}:{unique_id}"

        # Create DID Document
        doc = DIDDocument(
            id=did,
            controller=[controller],
            public_keys=public_keys or [],
            services=services or [],
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
            proof=None,
        )

        self._did_storage[did] = doc

        # Also create on Ethereum if available
        if self.ethereum and self.method == DIDMethod.ETHR:
            try:
                public_key_hash = (
                    "0x" + hashlib.sha256(controller.encode()).hexdigest()[:64]
                )
                service_json = json.dumps(services or [])
                self.ethereum.create_did(
                    did=controller,  # Use address portion
                    public_key_hash=public_key_hash,
                    service_endpoints=service_json,
                )
            except Exception as e:
                logger.warning(f"Could not register DID on Ethereum: {e}")

        logger.info(f"Created DID: {did}")
        return did

    def resolve_did(self, did: str) -> Optional[DIDDocument]:
        """
        Resolve DID to document

        Args:
            did: DID string

        Returns:
            DIDDocument or None
        """
        # Check local storage
        if did in self._did_storage:
            return self._did_storage[did]

        # Try to resolve from Ethereum
        if self.ethereum and did.startswith("did:ethr:"):
            try:
                address = did.replace("did:ethr:", "")
                doc = self.ethereum.did_registry.functions.didDocuments(
                    bytes.fromhex(address.replace("0x", "").zfill(64)[:64])
                ).call()

                if doc[3] > 0:  # created timestamp
                    return DIDDocument(
                        id=did,
                        controller=[address],
                        public_keys=[
                            {
                                "id": f"{did}#keys-1",
                                "type": "EcdsaSecp256k1VerificationKey2019",
                            }
                        ],
                        services=json.loads(doc[2]) if doc[2] else [],
                        created=datetime.fromtimestamp(doc[3]),
                        updated=datetime.fromtimestamp(doc[4]),
                        proof=None,
                    )
            except Exception as e:
                logger.error(f"Error resolving DID: {e}")

        return None

    def update_did(
        self,
        did: str,
        public_keys: Optional[List[Dict]] = None,
        services: Optional[List[Dict]] = None,
    ) -> bool:
        """
        Update DID Document

        Args:
            did: DID string
            public_keys: New public keys
            services: New services

        Returns:
            True if successful
        """
        doc = self.resolve_did(did)
        if not doc:
            return False

        if public_keys:
            doc.public_keys = public_keys
        if services:
            doc.services = services

        doc.updated = datetime.utcnow()
        self._did_storage[did] = doc

        return True

    def deactivate_did(self, did: str) -> bool:
        """
        Deactivate DID

        Args:
            did: DID string

        Returns:
            True if successful
        """
        doc = self.resolve_did(did)
        if not doc:
            return False

        # Mark as deactivated (in production, would add proper proof)
        doc.controller = []
        doc.updated = datetime.utcnow()

        return True

    # -------------------------------------------------------------------------
    # Verifiable Credentials
    # -------------------------------------------------------------------------

    def issue_credential(
        self,
        issuer_did: str,
        subject_did: str,
        claims: Dict,
        credential_type: List[str],
        expiration_days: Optional[int] = 365,
    ) -> VerifiableCredential:
        """
        Issue verifiable credential

        Args:
            issuer_did: Issuer DID
            subject_did: Subject DID
            claims: Credential claims
            credential_type: Credential type
            expiration_days: Days until expiration

        Returns:
            VerifiableCredential
        """
        # Verify issuer exists
        issuer_doc = self.resolve_did(issuer_did)
        if not issuer_doc:
            raise ValueError("Issuer DID not found")

        # Generate credential ID
        cred_id = f"urn:uuid:{hashlib.uuid4().hex}"

        # Calculate expiration
        issued_at = datetime.utcnow()
        expires_at = (
            issued_at + timedelta(days=expiration_days) if expiration_days else None
        )

        # Create credential
        credential = VerifiableCredential(
            id=cred_id,
            issuer=issuer_did,
            subject=subject_did,
            credential_type=credential_type,
            claims=claims,
            issued_at=issued_at,
            expires_at=expires_at,
            proof=None,  # Would add cryptographic proof
        )

        # Store
        self._credential_storage[cred_id] = credential

        # Also issue on Ethereum if available
        if self.ethereum:
            try:
                cred_hash = hashlib.sha256(json.dumps(claims).encode()).hexdigest()
                subject_bytes = bytes.fromhex(
                    subject_did.replace("did:ethr:", "")
                    .replace("0x", "")
                    .zfill(64)[:64]
                )
                fabric_anchor = "0x" + hashlib.sha256(cred_id.encode()).hexdigest()[:64]

                self.ethereum.issue_credential(
                    credential_hash="0x" + cred_hash[:64],
                    subject_did=subject_bytes.hex(),
                    expires_at=int(expires_at.timestamp()),
                    fabric_anchor=fabric_anchor,
                )
            except Exception as e:
                logger.warning(f"Could not issue credential on Ethereum: {e}")

        logger.info(f"Issued credential: {cred_id}")
        return credential

    def verify_credential(
        self, credential_id: str, issuer_did: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Verify credential validity

        Args:
            credential_id: Credential ID
            issuer_did: Expected issuer DID

        Returns:
            Tuple of (is_valid, reason)
        """
        credential = self._credential_storage.get(credential_id)

        if not credential:
            # Check Ethereum
            if self.ethereum and issuer_did:
                return self.ethereum.verify_credential(
                    credential_id.replace("urn:uuid:", ""),
                    issuer_did.replace("did:ethr:", ""),
                )
            return False, "Credential not found"

        # Check expiration
        if credential.expires_at and datetime.utcnow() > credential.expires_at:
            return False, "Credential expired"

        # Check issuer
        if issuer_did and credential.issuer != issuer_did:
            return False, "Issuer mismatch"

        # Verify issuer exists
        if not self.resolve_did(credential.issuer):
            return False, "Issuer DID not found or inactive"

        return True, "Valid"

    def revoke_credential(self, credential_id: str) -> bool:
        """
        Revoke credential

        Args:
            credential_id: Credential ID

        Returns:
            True if successful
        """
        credential = self._credential_storage.get(credential_id)
        if not credential:
            return False

        # Mark as revoked (in production, would add revocation proof)
        credential.expires_at = datetime.utcnow()

        return True

    def get_credentials_for_subject(
        self, subject_did: str
    ) -> List[VerifiableCredential]:
        """Get all credentials for a subject"""
        return [
            cred
            for cred in self._credential_storage.values()
            if cred.subject == subject_did
        ]

    # -------------------------------------------------------------------------
    # Presentation Generation
    # -------------------------------------------------------------------------

    def create_presentation(
        self,
        credential_ids: List[str],
        holder_did: str,
        challenge: Optional[str] = None,
    ) -> Dict:
        """
        Create verifiable presentation

        Args:
            credential_ids: Credentials to include
            holder_did: Holder DID
            challenge: Optional challenge string

        Returns:
            Presentation JSON-LD
        """
        credentials = [
            self._credential_storage[cid]
            for cid in credential_ids
            if cid in self._credential_storage
        ]

        holder_doc = self.resolve_did(holder_did)
        if not holder_doc:
            raise ValueError("Holder DID not found")

        presentation = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "type": ["VerifiablePresentation"],
            "holder": holder_did,
            "verifiableCredential": [
                {
                    "@context": ["https://www.w3.org/2018/credentials/v1"],
                    "id": cred.id,
                    "type": cred.credential_type,
                    "issuer": {"id": cred.issuer},
                    "credentialSubject": {"id": cred.subject, **cred.claims},
                    "issuanceDate": cred.issued_at.isoformat(),
                    "expirationDate": cred.expires_at.isoformat()
                    if cred.expires_at
                    else None,
                }
                for cred in credentials
            ],
            "proof": {
                "type": "Ed25519Signature2018",
                "created": datetime.utcnow().isoformat(),
                "challenge": challenge,
                "verificationMethod": f"{holder_did}#keys-1",
            },
        }

        return presentation

    # -------------------------------------------------------------------------
    # Utility Functions
    # -------------------------------------------------------------------------

    def generate_did_auth_challenge(self) -> str:
        """Generate DID authentication challenge"""
        return hashlib.sha256(f"{datetime.now().timestamp()}".encode()).hexdigest()

    def verify_did_auth(self, did: str, challenge: str, signature: str) -> bool:
        """
        Verify DID authentication

        Args:
            did: DID string
            challenge: Challenge that was signed
            signature: Signature to verify

        Returns:
            True if valid
        """
        doc = self.resolve_did(did)
        if not doc or not doc.public_keys:
            return False

        # In production, verify cryptographic signature
        # For demo, just check DID exists
        return True


# =============================================================================
# Section 4: Unified Blockchain Controller
# =============================================================================


class BlockchainController:
    """
    Unified controller for all blockchain integrations

    Coordinates:
    - Ethereum operations
    - Hyperledger Fabric operations
    - DID management
    - Cross-chain synchronization
    """

    def __init__(
        self,
        ethereum_config: Optional[Dict] = None,
        fabric_config: Optional[Dict] = None,
        did_config: Optional[Dict] = None,
    ):
        """
        Initialize unified controller

        Args:
            ethereum_config: Ethereum configuration
            fabric_config: Fabric configuration
            did_config: DID configuration
        """
        self.ethereum: Optional[EthereumIntegration] = None
        self.fabric: Optional[FabricIntegration] = None
        self.did_manager: Optional[DIDManager] = None

        # Initialize components
        if ethereum_config:
            self.ethereum = EthereumIntegration(**ethereum_config)

        if fabric_config:
            self.fabric = FabricIntegration(**fabric_config)

        if did_config:
            method = DIDMethod(did_config.get("method", "ethr"))
            self.did_manager = DIDManager(
                method=method,
                ethereum_integration=self.ethereum,
                fabric_integration=self.fabric,
            )
        else:
            # Create default DID manager
            self.did_manager = DIDManager(
                ethereum_integration=self.ethereum, fabric_integration=self.fabric
            )

        logger.info("Blockchain Controller initialized")

    # -------------------------------------------------------------------------
    # Cross-Chain Operations
    # -------------------------------------------------------------------------

    async def create_cross_chain_asset(
        self, asset_data: Dict, owner_eth_address: str, owner_did: str
    ) -> Dict[str, Any]:
        """
        Create asset on both Fabric and Ethereum

        Args:
            asset_data: Asset information
            owner_eth_address: Owner Ethereum address
            owner_did: Owner DID

        Returns:
            Cross-chain result
        """
        results = {"fabric": None, "ethereum": None, "did": None}

        # 1. Create DID if not exists
        if not self.did_manager.resolve_did(owner_did):
            self.did_manager.create_did(
                controller=owner_eth_address,
                services=[
                    {
                        "type": "NeuralBlitzAgent",
                        "endpoint": "https://agent.neuralblitz.ai",
                    }
                ],
            )
            results["did"] = owner_did

        # 2. Create on Fabric
        if self.fabric:
            fabric_result = await self.fabric.create_asset(
                asset_id=asset_data["id"],
                asset_type=asset_data["type"],
                owner=owner_eth_address,
                value=asset_data["value"],
                ethereum_token_id="0",  # Will be updated
                did=owner_did,
                confidential_data=asset_data.get("confidential"),
            )
            results["fabric"] = fabric_result

        # 3. Mint on Ethereum
        if self.ethereum:
            eth_result = self.ethereum.mint_asset(
                to_address=owner_eth_address,
                asset_type=asset_data["type"],
                fabric_record_hash=results["fabric"]["merkle_root"]
                if results["fabric"]
                else "0x0",
                did_reference=owner_did,
                attributes=asset_data.get("attributes", {}),
            )
            results["ethereum"] = eth_result

            # Update Fabric with Ethereum token ID
            if self.fabric and results["fabric"]:
                await self.fabric.update_asset(
                    asset_id=asset_data["id"],
                    new_value=asset_data["value"],
                    new_status="SYNCHRONIZED",
                )

        return results

    async def verify_cross_chain_asset(
        self, asset_id: str, token_id: int
    ) -> Dict[str, Any]:
        """
        Verify asset on both chains

        Args:
            asset_id: Fabric asset ID
            token_id: Ethereum token ID

        Returns:
            Verification result
        """
        verification = {
            "fabric_exists": False,
            "ethereum_exists": False,
            "ownership_verified": False,
            "details": {},
        }

        # Check Fabric
        if self.fabric:
            fabric_asset = await self.fabric.read_asset(asset_id)
            verification["fabric_exists"] = fabric_asset is not None
            if fabric_asset:
                verification["details"]["fabric"] = {
                    "owner": fabric_asset.owner,
                    "value": fabric_asset.value,
                    "merkle_root": fabric_asset.merkle_root,
                }

        # Check Ethereum
        if self.ethereum:
            eth_asset = self.ethereum.get_asset(token_id)
            verification["ethereum_exists"] = eth_asset is not None
            if eth_asset:
                verification["details"]["ethereum"] = {
                    "owner": eth_asset.owner,
                    "fabric_hash": eth_asset.fabric_record_hash,
                }

        # Verify ownership match
        if verification["fabric_exists"] and verification["ethereum_exists"]:
            if self.fabric and self.ethereum:
                verification["ownership_verified"] = (
                    self.ethereum.verify_cross_chain_ownership(
                        token_id, verification["details"]["fabric"]["merkle_root"]
                    )
                )

        return verification

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all blockchain integrations"""
        status = {"ethereum": "disconnected", "fabric": "disconnected", "did": "active"}

        if self.ethereum and self.ethereum.w3.is_connected():
            status["ethereum"] = f"connected (chain: {self.ethereum.w3.eth.chain_id})"

        if self.fabric:
            status["fabric"] = "initialized"

        return status


# =============================================================================
# Example Usage
# =============================================================================


async def example_usage():
    """Example demonstrating all integrations"""

    # Configuration (would come from environment/config in production)
    ETH_PRIVATE_KEY = os.getenv("ETH_PRIVATE_KEY", "0x" + "ab" * 32)
    PROVIDER_URL = os.getenv("ETH_PROVIDER_URL", "https://sepolia.infura.io/v3/demo")

    # Initialize Ethereum
    print("=== Initializing Ethereum ===")
    eth = EthereumIntegration(provider_url=PROVIDER_URL, private_key=ETH_PRIVATE_KEY)
    print(f"Ethereum connected: {eth.w3.is_connected()}")

    # Initialize Fabric (mock config)
    print("\n=== Initializing Fabric ===")
    fabric = FabricIntegration(
        network_config={"organizations": {}}, org_name="Org1", user_name="Admin"
    )
    print("Fabric initialized")

    # Initialize DID Manager
    print("\n=== Initializing DID Manager ===")
    did_mgr = DIDManager(method=DIDMethod.ETHR, ethereum_integration=eth)

    # Create DID
    user_did = did_mgr.create_did(
        controller=eth.account.address if eth.account else "0x000",
        services=[{"type": "AgentService", "endpoint": "https://agent.example.com"}],
    )
    print(f"Created DID: {user_did}")

    # Issue credential
    credential = did_mgr.issue_credential(
        issuer_did=user_did,
        subject_did=user_did,
        claims={"role": "NeuralBlitzOperator", "clearance": "level3"},
        credential_type=["VerifiableCredential", "NeuralBlitzCredential"],
        expiration_days=365,
    )
    print(f"Issued credential: {credential.id}")

    # Verify credential
    is_valid, reason = did_mgr.verify_credential(credential.id)
    print(f"Credential valid: {is_valid}, reason: {reason}")

    # Create cross-chain asset
    print("\n=== Creating Cross-Chain Asset ===")
    controller = BlockchainController(
        ethereum_config={"provider_url": PROVIDER_URL, "private_key": ETH_PRIVATE_KEY},
        did_config={"method": "ethr"},
    )

    # Note: Would need actual Fabric network for full demo
    # result = await controller.create_cross_chain_asset(
    #     asset_data={
    #         'id': 'property-001',
    #         'type': 'Property',
    #         'value': 500000,
    #         'attributes': {'location': 'NYC'}
    #     },
    #     owner_eth_address=eth.account.address if eth.account else "0x000",
    #     owner_did=user_did
    # )
    # print(f"Cross-chain result: {result}")

    print("\n=== System Status ===")
    print(controller.get_system_status())

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(example_usage())
