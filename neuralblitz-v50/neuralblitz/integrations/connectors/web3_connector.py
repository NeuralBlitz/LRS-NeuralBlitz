"""
Web3/Ethereum Integration Connector
Provides decentralized coordination capabilities via blockchain
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from decimal import Decimal

from .. import (
    BaseConnector,
    ConnectorConfig,
    ConnectorResponse,
    AuthenticationError,
    TimeoutError,
    retry_with_backoff,
    CircuitBreakerOpenError,
)

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Ethereum transaction structure"""

    to: str
    value: Decimal
    data: str = "0x"
    gas: int = 21000
    gas_price: Optional[int] = None
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    nonce: Optional[int] = None
    chain_id: int = 1


@dataclass
class TransactionReceipt:
    """Transaction receipt"""

    transaction_hash: str
    block_number: int
    block_hash: str
    gas_used: int
    status: bool
    logs: List[Dict]
    contract_address: Optional[str] = None


@dataclass
class SmartContractCall:
    """Smart contract function call"""

    contract_address: str
    function_name: str
    function_args: List[Any]
    abi: List[Dict]
    value: Decimal = Decimal("0")


class Web3Connector(BaseConnector):
    """Connector for Web3/Ethereum blockchain interaction"""

    DEFAULT_RPC_URLS = {
        "mainnet": "https://eth-mainnet.g.alchemy.com/v2/",
        "sepolia": "https://eth-sepolia.g.alchemy.com/v2/",
        "goerli": "https://eth-goerli.g.alchemy.com/v2/",
        "polygon": "https://polygon-mainnet.g.alchemy.com/v2/",
        "arbitrum": "https://arb-mainnet.g.alchemy.com/v2/",
        "optimism": "https://opt-mainnet.g.alchemy.com/v2/",
    }

    def __init__(self, config: ConnectorConfig, network: str = "mainnet"):
        super().__init__(config)
        self.network = network
        self.rpc_url = config.base_url or self.DEFAULT_RPC_URLS.get(
            network, self.DEFAULT_RPC_URLS["mainnet"]
        )
        self.api_key = config.api_key
        self.session: Optional[Any] = None
        self._web3 = None

        # Try to import web3
        try:
            from web3 import Web3
            from web3.middleware import geth_poa_middleware

            self.Web3 = Web3
            self.geth_poa_middleware = geth_poa_middleware
        except ImportError:
            logger.warning("web3.py not installed. Some features may be unavailable.")
            self.Web3 = None

    async def _get_web3(self):
        """Get or create Web3 instance"""
        if self._web3 is None and self.Web3:
            full_url = f"{self.rpc_url}{self.api_key}" if self.api_key else self.rpc_url
            self._web3 = self.Web3(self.Web3.HTTPProvider(full_url))

            # Add POA middleware for networks like Goerli
            if self.network in ["goerli", "sepolia"]:
                self._web3.middleware_onion.inject(self.geth_poa_middleware, layer=0)

        return self._web3

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_balance(
        self, address: str, block: Union[str, int] = "latest"
    ) -> ConnectorResponse:
        """Get ETH balance for an address"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            cache_key = self._get_cache_key("balance", address, block)
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._get_balance_sync, web3, address, block
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"address": address, "network": self.network},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return self._create_response(False, error=str(e))

    def _get_balance_sync(self, web3, address: str, block) -> Dict:
        """Synchronous balance retrieval"""
        checksum_address = web3.to_checksum_address(address)
        balance_wei = web3.eth.get_balance(checksum_address, block_identifier=block)
        balance_eth = web3.from_wei(balance_wei, "ether")

        return {
            "address": address,
            "balance_wei": balance_wei,
            "balance_eth": str(balance_eth),
            "block": block,
        }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def send_transaction(
        self, transaction: Transaction, private_key: str
    ) -> ConnectorResponse:
        """Send a signed transaction"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            result, latency = await self._execute_with_protection(
                self._send_transaction_sync, web3, transaction, private_key
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"network": self.network},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Send transaction failed: {e}")
            return self._create_response(False, error=str(e))

    def _send_transaction_sync(
        self, web3, transaction: Transaction, private_key: str
    ) -> Dict:
        """Synchronous transaction sending"""
        account = web3.eth.account.from_key(private_key)

        # Build transaction
        tx_dict = {
            "to": web3.to_checksum_address(transaction.to),
            "value": web3.to_wei(transaction.value, "ether"),
            "data": transaction.data,
            "gas": transaction.gas,
            "chainId": transaction.chain_id,
        }

        # Add nonce
        if transaction.nonce is None:
            tx_dict["nonce"] = web3.eth.get_transaction_count(account.address)
        else:
            tx_dict["nonce"] = transaction.nonce

        # Handle gas pricing (EIP-1559 or legacy)
        if transaction.max_fee_per_gas and transaction.max_priority_fee_per_gas:
            tx_dict["maxFeePerGas"] = transaction.max_fee_per_gas
            tx_dict["maxPriorityFeePerGas"] = transaction.max_priority_fee_per_gas
        elif transaction.gas_price:
            tx_dict["gasPrice"] = transaction.gas_price
        else:
            # Auto-estimate
            tx_dict["gasPrice"] = web3.eth.gas_price

        # Sign transaction
        signed_tx = web3.eth.account.sign_transaction(tx_dict, private_key)

        # Send transaction
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return {
            "transaction_hash": tx_hash.hex(),
            "from": account.address,
            "to": transaction.to,
            "value": str(transaction.value),
            "gas": transaction.gas,
            "nonce": tx_dict["nonce"],
        }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_transaction_receipt(self, tx_hash: str) -> ConnectorResponse:
        """Get transaction receipt"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            result, latency = await self._execute_with_protection(
                self._get_receipt_sync, web3, tx_hash
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"transaction_hash": tx_hash},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Get receipt failed: {e}")
            return self._create_response(False, error=str(e))

    def _get_receipt_sync(self, web3, tx_hash: str) -> Optional[Dict]:
        """Synchronous receipt retrieval"""
        receipt = web3.eth.get_transaction_receipt(tx_hash)

        if receipt is None:
            return None

        return {
            "transaction_hash": receipt["transactionHash"].hex(),
            "block_number": receipt["blockNumber"],
            "block_hash": receipt["blockHash"].hex(),
            "gas_used": receipt["gasUsed"],
            "status": receipt["status"] == 1,
            "logs": [dict(log) for log in receipt["logs"]],
            "contract_address": receipt.get("contractAddress"),
        }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def call_contract_function(
        self, call: SmartContractCall
    ) -> ConnectorResponse:
        """Call a smart contract function (read-only)"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            result, latency = await self._execute_with_protection(
                self._call_contract_sync, web3, call
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={
                    "contract": call.contract_address,
                    "function": call.function_name,
                },
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Contract call failed: {e}")
            return self._create_response(False, error=str(e))

    def _call_contract_sync(self, web3, call: SmartContractCall) -> Any:
        """Synchronous contract call"""
        contract = web3.eth.contract(
            address=web3.to_checksum_address(call.contract_address), abi=call.abi
        )

        function = getattr(contract.functions, call.function_name)
        result = function(*call.function_args).call()

        return result

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def estimate_gas(self, transaction: Transaction) -> ConnectorResponse:
        """Estimate gas for a transaction"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            result, latency = await self._execute_with_protection(
                self._estimate_gas_sync, web3, transaction
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"network": self.network},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Gas estimation failed: {e}")
            return self._create_response(False, error=str(e))

    def _estimate_gas_sync(self, web3, transaction: Transaction) -> Dict:
        """Synchronous gas estimation"""
        tx_dict = {
            "to": web3.to_checksum_address(transaction.to),
            "value": web3.to_wei(transaction.value, "ether"),
            "data": transaction.data,
        }

        estimated_gas = web3.eth.estimate_gas(tx_dict)
        gas_price = web3.eth.gas_price

        return {
            "estimated_gas": estimated_gas,
            "gas_price": gas_price,
            "estimated_cost_wei": estimated_gas * gas_price,
            "estimated_cost_eth": str(
                web3.from_wei(estimated_gas * gas_price, "ether")
            ),
        }

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_block(self, block_identifier: Union[str, int]) -> ConnectorResponse:
        """Get block information"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            cache_key = self._get_cache_key("block", block_identifier)
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._get_block_sync, web3, block_identifier
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"network": self.network},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Get block failed: {e}")
            return self._create_response(False, error=str(e))

    def _get_block_sync(self, web3, block_identifier) -> Dict:
        """Synchronous block retrieval"""
        block = web3.eth.get_block(block_identifier, full_transactions=False)

        return {
            "number": block["number"],
            "hash": block["hash"].hex(),
            "parent_hash": block["parentHash"].hex(),
            "timestamp": block["timestamp"],
            "gas_used": block["gasUsed"],
            "gas_limit": block["gasLimit"],
            "transactions_count": len(block["transactions"]),
            "miner": block["miner"],
        }

    async def health_check(self) -> ConnectorResponse:
        """Check Web3 connection health"""
        try:
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not initialized")

            is_connected = web3.is_connected()
            block_number = web3.eth.block_number if is_connected else None

            return self._create_response(
                success=is_connected,
                data={
                    "status": "healthy" if is_connected else "unhealthy",
                    "connected": is_connected,
                    "block_number": block_number,
                    "network": self.network,
                },
                metadata={"network": self.network},
            )
        except Exception as e:
            return self._create_response(False, error=str(e))

    async def close(self):
        """Clean up resources"""
        if self._web3:
            # Web3 doesn't require explicit cleanup for HTTP provider
            self._web3 = None


class DecentralizedCoordinationConnector(Web3Connector):
    """
    Extended connector for decentralized coordination patterns
    Supports multi-sig, DAO interactions, and cross-chain coordination
    """

    def __init__(self, config: ConnectorConfig, network: str = "mainnet"):
        super().__init__(config, network)
        self.coordination_contracts = {}

    async def register_coordination_contract(
        self, name: str, address: str, abi: List[Dict]
    ):
        """Register a coordination smart contract"""
        self.coordination_contracts[name] = {"address": address, "abi": abi}
        logger.info(f"Registered coordination contract: {name}")

    async def propose_action(
        self,
        contract_name: str,
        action_type: str,
        parameters: Dict[str, Any],
        proposer_private_key: str,
    ) -> ConnectorResponse:
        """Propose a coordinated action via smart contract"""
        try:
            if contract_name not in self.coordination_contracts:
                return self._create_response(
                    False, error=f"Contract '{contract_name}' not registered"
                )

            contract_info = self.coordination_contracts[contract_name]

            # Create function call
            call = SmartContractCall(
                contract_address=contract_info["address"],
                function_name="propose",
                function_args=[action_type, json.dumps(parameters)],
                abi=contract_info["abi"],
                value=Decimal("0"),
            )

            # Execute proposal (requires transaction)
            web3 = await self._get_web3()
            if not web3:
                return self._create_response(False, error="Web3 not available")

            result, latency = await self._execute_with_protection(
                self._execute_proposal, web3, call, proposer_private_key
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"contract": contract_name, "action": action_type},
            )

        except Exception as e:
            logger.error(f"Propose action failed: {e}")
            return self._create_response(False, error=str(e))

    def _execute_proposal(
        self, web3, call: SmartContractCall, private_key: str
    ) -> Dict:
        """Execute proposal transaction"""
        account = web3.eth.account.from_key(private_key)

        contract = web3.eth.contract(
            address=web3.to_checksum_address(call.contract_address), abi=call.abi
        )

        # Build transaction
        tx = contract.functions[call.function_name](
            *call.function_args
        ).build_transaction(
            {
                "from": account.address,
                "nonce": web3.eth.get_transaction_count(account.address),
                "gas": 200000,
                "gasPrice": web3.eth.gas_price,
            }
        )

        # Sign and send
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return {
            "transaction_hash": tx_hash.hex(),
            "proposal_id": None,  # Would be returned from contract event
            "proposer": account.address,
        }

    async def get_coordination_state(self, contract_name: str) -> ConnectorResponse:
        """Get current state of coordination contract"""
        try:
            if contract_name not in self.coordination_contracts:
                return self._create_response(
                    False, error=f"Contract '{contract_name}' not registered"
                )

            contract_info = self.coordination_contracts[contract_name]

            # Call getState function
            call = SmartContractCall(
                contract_address=contract_info["address"],
                function_name="getState",
                function_args=[],
                abi=contract_info["abi"],
            )

            return await self.call_contract_function(call)

        except Exception as e:
            return self._create_response(False, error=str(e))
