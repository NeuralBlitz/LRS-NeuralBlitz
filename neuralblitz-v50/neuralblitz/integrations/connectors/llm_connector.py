"""
OpenAI GPT-4 / Anthropic Claude Integration Connector
Supports hybrid reasoning with fallback and ensemble capabilities
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
import aiohttp
from dataclasses import dataclass

from .. import (
    BaseConnector,
    ConnectorConfig,
    ConnectorResponse,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    retry_with_backoff,
    CircuitBreakerOpenError,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Message structure for LLM conversations"""

    role: str  # system, user, assistant
    content: str
    metadata: Optional[Dict] = None


@dataclass
class LLMRequest:
    """Request structure for LLM inference"""

    messages: List[LLMMessage]
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False


@dataclass
class LLMResponse:
    """Response structure from LLM"""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    latency_ms: float
    metadata: Dict[str, Any]


class OpenAIConnector(BaseConnector):
    """Connector for OpenAI GPT-4 API"""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    def _validate_request(self, request: LLMRequest) -> None:
        """Validate LLM request parameters"""
        if not request.messages:
            raise ValueError("Messages cannot be empty")

        if request.temperature < 0 or request.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if request.max_tokens < 1 or request.max_tokens > 4096:
            raise ValueError("Max tokens must be between 1 and 4096")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def generate(self, request: LLMRequest) -> ConnectorResponse:
        """Generate completion using OpenAI API"""
        try:
            # Validate request
            self._validate_request(request)

            # Check cache
            cache_key = self._get_cache_key(
                json.dumps(
                    [{"role": m.role, "content": m.content} for m in request.messages]
                ),
                request.model,
                request.temperature,
                request.max_tokens,
            )
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info("Cache hit for OpenAI request")
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            # Execute with protection
            result, latency = await self._execute_with_protection(
                self._call_api, request
            )

            # Cache result
            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"model": request.model, "provider": "openai"},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._create_response(False, error=str(e))

    async def _call_api(self, request: LLMRequest) -> LLMResponse:
        """Make actual API call to OpenAI"""
        session = await self._get_session()

        payload = {
            "model": request.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream,
        }

        try:
            async with session.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid OpenAI API key")
                elif response.status == 429:
                    raise RateLimitError("OpenAI rate limit exceeded")
                elif response.status == 408:
                    raise TimeoutError("OpenAI request timeout")
                elif response.status >= 500:
                    raise Exception(f"OpenAI server error: {response.status}")

                response.raise_for_status()
                data = await response.json()

                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data["model"],
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason", "unknown"),
                    latency_ms=0.0,  # Will be set by caller
                    metadata={"provider": "openai", "id": data.get("id")},
                )

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    async def health_check(self) -> ConnectorResponse:
        """Check OpenAI API health"""
        try:
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hello")],
                model="gpt-3.5-turbo",
                max_tokens=5,
            )
            result = await self.generate(test_request)
            return self._create_response(
                success=result.success,
                data={"status": "healthy" if result.success else "unhealthy"},
                error=result.error,
                latency_ms=result.latency_ms,
            )
        except Exception as e:
            return self._create_response(False, error=str(e))

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()


class ClaudeConnector(BaseConnector):
    """Connector for Anthropic Claude API"""

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def generate(self, request: LLMRequest) -> ConnectorResponse:
        """Generate completion using Claude API"""
        try:
            cache_key = self._get_cache_key(
                json.dumps(
                    [{"role": m.role, "content": m.content} for m in request.messages]
                ),
                request.model,
                request.temperature,
                request.max_tokens,
            )
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._call_api, request
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"model": request.model, "provider": "claude"},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            return self._create_response(False, error=str(e))

    async def _call_api(self, request: LLMRequest) -> LLMResponse:
        """Make actual API call to Claude"""
        session = await self._get_session()

        # Convert messages to Claude format
        system_message = ""
        user_messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": request.model,
            "messages": user_messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }

        if system_message:
            payload["system"] = system_message

        try:
            async with session.post(
                f"{self.base_url}/messages", headers=self.headers, json=payload
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Claude API key")
                elif response.status == 429:
                    raise RateLimitError("Claude rate limit exceeded")

                response.raise_for_status()
                data = await response.json()

                return LLMResponse(
                    content=data["content"][0]["text"],
                    model=data["model"],
                    usage=data.get("usage", {}),
                    finish_reason=data.get("stop_reason", "unknown"),
                    latency_ms=0.0,
                    metadata={"provider": "claude", "id": data.get("id")},
                )

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    async def health_check(self) -> ConnectorResponse:
        """Check Claude API health"""
        try:
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hello")],
                model="claude-3-haiku-20240307",
                max_tokens=5,
            )
            result = await self.generate(test_request)
            return self._create_response(
                success=result.success,
                data={"status": "healthy" if result.success else "unhealthy"},
                error=result.error,
                latency_ms=result.latency_ms,
            )
        except Exception as e:
            return self._create_response(False, error=str(e))

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()


class HybridReasoningConnector(BaseConnector):
    """
    Hybrid connector that combines OpenAI and Claude for robust reasoning
    Supports fallback, ensemble, and consensus modes
    """

    class Mode:
        FALLBACK = "fallback"  # Try primary, fallback to secondary
        ENSEMBLE = "ensemble"  # Query both and combine
        CONSENSUS = "consensus"  # Both must agree

    def __init__(self, openai_config: ConnectorConfig, claude_config: ConnectorConfig):
        super().__init__(openai_config)  # Use OpenAI config as base
        self.openai = OpenAIConnector(openai_config)
        self.claude = ClaudeConnector(claude_config)
        self.mode = self.Mode.FALLBACK
        self.primary = "openai"

    def set_mode(self, mode: str, primary: str = "openai"):
        """Set hybrid reasoning mode"""
        self.mode = mode
        self.primary = primary

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    async def generate(self, request: LLMRequest) -> ConnectorResponse:
        """Generate with hybrid reasoning strategy"""

        if self.mode == self.Mode.FALLBACK:
            return await self._fallback_mode(request)
        elif self.mode == self.Mode.ENSEMBLE:
            return await self._ensemble_mode(request)
        elif self.mode == self.Mode.CONSENSUS:
            return await self._consensus_mode(request)
        else:
            return self._create_response(False, error=f"Unknown mode: {self.mode}")

    async def _fallback_mode(self, request: LLMRequest) -> ConnectorResponse:
        """Try primary, fallback to secondary on failure"""
        primary_conn = self.openai if self.primary == "openai" else self.claude
        secondary_conn = self.claude if self.primary == "openai" else self.openai

        # Try primary
        result = await primary_conn.generate(request)
        if result.success:
            return self._create_response(
                True,
                data=result.data,
                latency_ms=result.latency_ms,
                metadata={
                    "provider": self.primary,
                    "mode": "fallback",
                    "used": "primary",
                },
            )

        logger.warning(f"Primary {self.primary} failed, trying fallback")

        # Try secondary
        result = await secondary_conn.generate(request)
        if result.success:
            return self._create_response(
                True,
                data=result.data,
                latency_ms=result.latency_ms,
                metadata={
                    "provider": "secondary",
                    "mode": "fallback",
                    "used": "secondary",
                },
            )

        return self._create_response(
            False,
            error="Both primary and fallback providers failed",
            metadata={"primary_error": result.error},
        )

    async def _ensemble_mode(self, request: LLMRequest) -> ConnectorResponse:
        """Query both and combine results"""
        # Run both in parallel
        openai_task = self.openai.generate(request)
        claude_task = self.claude.generate(request)

        results = await asyncio.gather(openai_task, claude_task, return_exceptions=True)

        openai_result = results[0] if not isinstance(results[0], Exception) else None
        claude_result = results[1] if not isinstance(results[1], Exception) else None

        # Combine responses
        combined = {
            "openai": openai_result.data
            if openai_result and openai_result.success
            else None,
            "claude": claude_result.data
            if claude_result and claude_result.success
            else None,
        }

        success = (openai_result and openai_result.success) or (
            claude_result and claude_result.success
        )

        return self._create_response(
            success,
            data=combined,
            latency_ms=max(
                openai_result.latency_ms if openai_result else 0,
                claude_result.latency_ms if claude_result else 0,
            ),
            metadata={
                "mode": "ensemble",
                "openai_success": openai_result.success if openai_result else False,
                "claude_success": claude_result.success if claude_result else False,
            },
        )

    async def _consensus_mode(self, request: LLMRequest) -> ConnectorResponse:
        """Both providers must succeed"""
        openai_result = await self.openai.generate(request)
        claude_result = await self.claude.generate(request)

        if not openai_result.success or not claude_result.success:
            return self._create_response(
                False,
                error="Consensus not reached - one or both providers failed",
                metadata={
                    "openai_error": openai_result.error,
                    "claude_error": claude_result.error,
                },
            )

        return self._create_response(
            True,
            data={
                "openai": openai_result.data,
                "claude": claude_result.data,
                "consensus_reached": True,
            },
            latency_ms=openai_result.latency_ms + claude_result.latency_ms,
            metadata={"mode": "consensus"},
        )

    async def health_check(self) -> ConnectorResponse:
        """Check health of both providers"""
        openai_health = await self.openai.health_check()
        claude_health = await self.claude.health_check()

        return self._create_response(
            success=openai_health.success and claude_health.success,
            data={
                "openai": openai_health.data,
                "claude": claude_health.data,
                "overall": "healthy"
                if (openai_health.success and claude_health.success)
                else "degraded",
            },
            metadata={
                "openai_latency": openai_health.latency_ms,
                "claude_latency": claude_health.latency_ms,
            },
        )

    async def close(self):
        """Close both connectors"""
        await asyncio.gather(self.openai.close(), self.claude.close())
