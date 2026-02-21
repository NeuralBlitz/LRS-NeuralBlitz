"""
Integration Connector Usage Examples
Demonstrates usage of OpenAI, HuggingFace, and Web3 connectors
"""

import asyncio
import os
from decimal import Decimal

from neuralblitz_v50.neuralblitz.integrations import (
    ConnectorConfig,
    ConnectorManager,
    connector_manager,
)
from neuralblitz_v50.neuralblitz.integrations.connectors.llm_connector import (
    OpenAIConnector,
    ClaudeConnector,
    HybridReasoningConnector,
    LLMRequest,
    LLMMessage,
)
from neuralblitz_v50.neuralblitz.integrations.connectors.huggingface_connector import (
    HuggingFaceConnector,
    InferenceRequest,
)
from neuralblitz_v50.neuralblitz.integrations.connectors.web3_connector import (
    Web3Connector,
    DecentralizedCoordinationConnector,
    Transaction,
    SmartContractCall,
)


async def example_openai_connector():
    """Example: OpenAI GPT-4 Integration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: OpenAI GPT-4 Integration")
    print("=" * 60)

    # Configure connector
    config = ConnectorConfig(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        timeout=30.0,
        max_retries=3,
        rate_limit_per_second=5.0,
        enable_caching=True,
    )

    # Initialize connector
    openai = OpenAIConnector(config)

    # Create a conversation
    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are a helpful AI assistant."),
            LLMMessage(
                role="user", content="Explain quantum computing in simple terms."
            ),
        ],
        model="gpt-4",
        temperature=0.7,
        max_tokens=500,
    )

    # Generate response
    print("Sending request to OpenAI GPT-4...")
    response = await openai.generate(request)

    if response.success:
        result = response.data
        print(f"✓ Success! (Latency: {response.latency_ms:.2f}ms)")
        print(f"Model: {result.model}")
        print(f"Content: {result.content[:200]}...")
        print(f"Usage: {result.usage}")
    else:
        print(f"✗ Error: {response.error}")

    # Health check
    print("\nHealth Check:")
    health = await openai.health_check()
    print(f"Status: {'✓ Healthy' if health.success else '✗ Unhealthy'}")

    await openai.close()


async def example_claude_connector():
    """Example: Anthropic Claude Integration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Anthropic Claude Integration")
    print("=" * 60)

    config = ConnectorConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here"),
        timeout=30.0,
        max_retries=3,
        rate_limit_per_second=5.0,
    )

    claude = ClaudeConnector(config)

    request = LLMRequest(
        messages=[
            LLMMessage(role="user", content="What are the ethical implications of AI?")
        ],
        model="claude-3-opus-20240229",
        temperature=0.7,
        max_tokens=500,
    )

    print("Sending request to Claude...")
    response = await claude.generate(request)

    if response.success:
        result = response.data
        print(f"✓ Success! (Latency: {response.latency_ms:.2f}ms)")
        print(f"Model: {result.model}")
        print(f"Content: {result.content[:200]}...")
    else:
        print(f"✗ Error: {response.error}")

    await claude.close()


async def example_hybrid_reasoning():
    """Example: Hybrid Reasoning with OpenAI + Claude"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Hybrid Reasoning (OpenAI + Claude)")
    print("=" * 60)

    openai_config = ConnectorConfig(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
        rate_limit_per_second=3.0,
    )

    claude_config = ConnectorConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-api-key-here"),
        rate_limit_per_second=3.0,
    )

    # Initialize hybrid connector
    hybrid = HybridReasoningConnector(openai_config, claude_config)

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content="Analyze the trade-offs between centralization and decentralization.",
            )
        ],
        model="gpt-4",
        max_tokens=300,
    )

    # Test fallback mode
    print("\n1. Fallback Mode (OpenAI primary, Claude fallback):")
    hybrid.set_mode(HybridReasoningConnector.Mode.FALLBACK, primary="openai")
    response = await hybrid.generate(request)

    if response.success:
        print(f"✓ Success! Provider: {response.metadata.get('provider')}")
        print(f"Latency: {response.latency_ms:.2f}ms")
    else:
        print(f"✗ Error: {response.error}")

    # Test ensemble mode
    print("\n2. Ensemble Mode (query both, combine results):")
    hybrid.set_mode(HybridReasoningConnector.Mode.ENSEMBLE)
    response = await hybrid.generate(request)

    if response.success:
        data = response.data
        print(f"✓ Success! Both providers queried")
        print(f"OpenAI success: {response.metadata.get('openai_success')}")
        print(f"Claude success: {response.metadata.get('claude_success')}")
    else:
        print(f"✗ Error: {response.error}")

    await hybrid.close()


async def example_huggingface_connector():
    """Example: HuggingFace Hub Integration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: HuggingFace Hub Integration")
    print("=" * 60)

    config = ConnectorConfig(
        api_key=os.getenv("HF_API_TOKEN", "your-token-here"),
        timeout=60.0,
        max_retries=3,
        rate_limit_per_second=10.0,
    )

    hf = HuggingFaceConnector(config)

    # Search for models
    print("\n1. Searching for BERT models:")
    response = await hf.search_models(
        query="bert", filter_tags=["transformers", "pytorch"], limit=3
    )

    if response.success:
        models = response.data
        print(f"✓ Found {len(models)} models")
        for model in models:
            print(f"  - {model.model_id} ({model.downloads} downloads)")
    else:
        print(f"✗ Error: {response.error}")

    # Get model info
    print("\n2. Getting model info:")
    response = await hf.get_model_info("bert-base-uncased")

    if response.success:
        model = response.data
        print(f"✓ Model: {model.model_id}")
        print(f"  Pipeline: {model.pipeline_tag}")
        print(f"  Downloads: {model.downloads}")
        print(f"  Tags: {', '.join(model.tags[:5])}")
    else:
        print(f"✗ Error: {response.error}")

    # Run inference (example - would need actual API token)
    print("\n3. Running inference (mock):")
    request = InferenceRequest(
        model_id="bert-base-uncased",
        inputs="The quick brown fox jumps over the lazy dog.",
        parameters={"task": "feature-extraction"},
    )

    # Note: This would fail without valid token, shown for API demonstration
    # response = await hf.run_inference(request)
    print("  (Requires valid HF token - API call structure demonstrated)")

    await hf.close()


async def example_web3_connector():
    """Example: Web3/Ethereum Integration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Web3/Ethereum Integration")
    print("=" * 60)

    # Note: These are example values - use test networks for development
    config = ConnectorConfig(api_key=os.getenv("ALCHEMY_API_KEY", "demo"), timeout=30.0)

    # Use Sepolia testnet for examples
    web3 = Web3Connector(config, network="sepolia")

    print("\n1. Checking connection health:")
    health = await web3.health_check()

    if health.success:
        data = health.data
        print(f"✓ Connected to {data['network']}")
        print(f"  Block number: {data['block_number']}")
    else:
        print(f"✗ Connection failed: {health.error}")
        print("  (Expected without valid RPC endpoint)")

    # Get balance example
    print("\n2. Getting balance (example address):")
    test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    response = await web3.get_balance(test_address)

    if response.success:
        data = response.data
        print(f"✓ Balance for {data['address'][:20]}...")
        print(f"  {data['balance_eth']} ETH")
    else:
        print(f"✗ Error: {response.error}")
        print("  (Expected without valid connection)")

    # Gas estimation example
    print("\n3. Estimating gas for transaction:")
    tx = Transaction(
        to="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", value=Decimal("0.1"), data="0x"
    )

    response = await web3.estimate_gas(tx)

    if response.success:
        data = response.data
        print(f"✓ Estimated gas: {data['estimated_gas']}")
        print(f"  Cost: {data['estimated_cost_eth']} ETH")
    else:
        print(f"✗ Error: {response.error}")

    await web3.close()


async def example_decentralized_coordination():
    """Example: Decentralized Coordination"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Decentralized Coordination")
    print("=" * 60)

    config = ConnectorConfig(api_key=os.getenv("ALCHEMY_API_KEY", "demo"), timeout=30.0)

    coord = DecentralizedCoordinationConnector(config, network="sepolia")

    # Register a coordination contract (example)
    print("\n1. Registering coordination contract:")

    # Example DAO/Coordination contract ABI
    example_abi = [
        {
            "inputs": [],
            "name": "getState",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "string", "name": "actionType", "type": "string"},
                {"internalType": "string", "name": "parameters", "type": "string"},
            ],
            "name": "propose",
            "outputs": [
                {"internalType": "uint256", "name": "proposalId", "type": "uint256"}
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]

    await coord.register_coordination_contract(
        name="neural_coordination_dao",
        address="0x1234567890123456789012345678901234567890",
        abi=example_abi,
    )

    print("✓ Contract registered: neural_coordination_dao")

    print("\n2. Coordination patterns supported:")
    print("  - Multi-signature coordination")
    print("  - DAO proposal and voting")
    print("  - Cross-chain message passing")
    print("  - Decentralized identity verification")
    print("  - Smart contract orchestration")

    await coord.close()


async def example_connector_manager():
    """Example: Using Connector Manager"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Connector Manager")
    print("=" * 60)

    # Create manager
    manager = ConnectorManager()

    # Register connectors
    openai_config = ConnectorConfig(
        api_key=os.getenv("OPENAI_API_KEY", "demo"), rate_limit_per_second=5.0
    )

    hf_config = ConnectorConfig(
        api_key=os.getenv("HF_API_TOKEN", "demo"), rate_limit_per_second=10.0
    )

    openai = OpenAIConnector(openai_config)
    hf = HuggingFaceConnector(hf_config)

    manager.register_connector("openai", openai)
    manager.register_connector("huggingface", hf)

    print("\n1. Registered connectors:")
    for name in manager.connectors.keys():
        print(f"  - {name}")

    print("\n2. Health check all:")
    health_results = await manager.health_check_all()
    for name, result in health_results.items():
        status = "✓" if result.success else "✗"
        print(f"  {status} {name}: {result.data if result.success else result.error}")

    print("\n3. Metrics:")
    metrics = manager.get_metrics()
    for name, metric in metrics.items():
        print(f"  {name}:")
        print(f"    Total requests: {metric['total_requests']}")
        print(f"    Successful: {metric['successful_requests']}")
        print(f"    Failed: {metric['failed_requests']}")

    await manager.close_all()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("NeuralBlitz Integration Connectors - Usage Examples")
    print("=" * 60)
    print("\nNote: Some examples require valid API keys")
    print("Set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY,")
    print("HF_API_TOKEN, ALCHEMY_API_KEY")

    try:
        # Run examples
        await example_openai_connector()
        await example_claude_connector()
        await example_hybrid_reasoning()
        await example_huggingface_connector()
        await example_web3_connector()
        await example_decentralized_coordination()
        await example_connector_manager()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
