"""
HuggingFace Hub Integration Connector
Provides access to models, datasets, and spaces from HuggingFace
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union, BinaryIO
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
class ModelInfo:
    """Information about a HuggingFace model"""

    model_id: str
    pipeline_tag: str
    tags: List[str]
    downloads: int
    likes: int
    last_modified: str
    config: Dict[str, Any]
    card_data: Optional[Dict] = None


@dataclass
class InferenceRequest:
    """Request for model inference"""

    model_id: str
    inputs: Union[str, List, Dict]
    parameters: Optional[Dict] = None
    options: Optional[Dict] = None


@dataclass
class InferenceResponse:
    """Response from model inference"""

    output: Any
    model_id: str
    inference_time_ms: float
    metadata: Dict[str, Any]


class HuggingFaceConnector(BaseConnector):
    """Connector for HuggingFace Hub API"""

    DEFAULT_BASE_URL = "https://huggingface.co/api"
    INFERENCE_API_URL = "https://api-inference.huggingface.co"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.inference_url = self.INFERENCE_API_URL
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

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def search_models(
        self,
        query: str = "",
        filter_tags: Optional[List[str]] = None,
        sort: str = "downloads",
        limit: int = 10,
    ) -> ConnectorResponse:
        """Search for models on HuggingFace Hub"""
        try:
            cache_key = self._get_cache_key(
                "search_models", query, filter_tags, sort, limit
            )
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._search_models_api, query, filter_tags, sort, limit
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"query": query, "count": len(result)},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Model search failed: {e}")
            return self._create_response(False, error=str(e))

    async def _search_models_api(
        self, query: str, filter_tags: Optional[List[str]], sort: str, limit: int
    ) -> List[ModelInfo]:
        """Make API call to search models"""
        session = await self._get_session()

        params = {"search": query, "sort": sort, "limit": limit}

        if filter_tags:
            params["filter"] = ",".join(filter_tags)

        try:
            async with session.get(
                f"{self.base_url}/models", headers=self.headers, params=params
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid HuggingFace API token")
                elif response.status == 429:
                    raise RateLimitError("HuggingFace rate limit exceeded")

                response.raise_for_status()
                data = await response.json()

                models = []
                for item in data:
                    model = ModelInfo(
                        model_id=item.get("id"),
                        pipeline_tag=item.get("pipeline_tag", "unknown"),
                        tags=item.get("tags", []),
                        downloads=item.get("downloads", 0),
                        likes=item.get("likes", 0),
                        last_modified=item.get("lastModified", ""),
                        config=item.get("config", {}),
                        card_data=item.get("cardData", {}),
                    )
                    models.append(model)

                return models

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def get_model_info(self, model_id: str) -> ConnectorResponse:
        """Get detailed information about a model"""
        try:
            cache_key = self._get_cache_key("model_info", model_id)
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._get_model_info_api, model_id
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"model_id": model_id},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Get model info failed: {e}")
            return self._create_response(False, error=str(e))

    async def _get_model_info_api(self, model_id: str) -> ModelInfo:
        """Make API call to get model info"""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/models/{model_id}", headers=self.headers
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid HuggingFace API token")
                elif response.status == 404:
                    raise ValueError(f"Model '{model_id}' not found")
                elif response.status == 429:
                    raise RateLimitError("HuggingFace rate limit exceeded")

                response.raise_for_status()
                data = await response.json()

                return ModelInfo(
                    model_id=data.get("id"),
                    pipeline_tag=data.get("pipeline_tag", "unknown"),
                    tags=data.get("tags", []),
                    downloads=data.get("downloads", 0),
                    likes=data.get("likes", 0),
                    last_modified=data.get("lastModified", ""),
                    config=data.get("config", {}),
                    card_data=data.get("cardData", {}),
                )

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def run_inference(self, request: InferenceRequest) -> ConnectorResponse:
        """Run inference using HuggingFace Inference API"""
        try:
            result, latency = await self._execute_with_protection(
                self._run_inference_api, request
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"model_id": request.model_id},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return self._create_response(False, error=str(e))

    async def _run_inference_api(self, request: InferenceRequest) -> InferenceResponse:
        """Make API call for inference"""
        session = await self._get_session()

        payload = {"inputs": request.inputs}

        if request.parameters:
            payload["parameters"] = request.parameters

        if request.options:
            payload["options"] = request.options

        try:
            async with session.post(
                f"{self.inference_url}/models/{request.model_id}",
                headers=self.headers,
                json=payload,
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid HuggingFace API token")
                elif response.status == 429:
                    raise RateLimitError("HuggingFace rate limit exceeded")
                elif response.status == 503:
                    # Model is loading
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.info(f"Model loading, retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise TimeoutError("Model is loading, please retry")

                response.raise_for_status()
                data = await response.json()

                return InferenceResponse(
                    output=data,
                    model_id=request.model_id,
                    inference_time_ms=0.0,
                    metadata={"provider": "huggingface"},
                )

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    async def download_model_file(
        self, model_id: str, filename: str, revision: str = "main"
    ) -> ConnectorResponse:
        """Download a specific file from a model repository"""
        try:
            result, latency = await self._execute_with_protection(
                self._download_file_api, model_id, filename, revision
            )

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"model_id": model_id, "filename": filename},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return self._create_response(False, error=str(e))

    async def _download_file_api(
        self, model_id: str, filename: str, revision: str
    ) -> bytes:
        """Make API call to download file"""
        session = await self._get_session()

        url = f"https://huggingface.co/{model_id}/resolve/{revision}/{filename}"

        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid HuggingFace API token")
                elif response.status == 404:
                    raise ValueError(
                        f"File '{filename}' not found in model '{model_id}'"
                    )

                response.raise_for_status()
                return await response.read()

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    async def list_datasets(
        self, query: str = "", limit: int = 10
    ) -> ConnectorResponse:
        """Search for datasets on HuggingFace Hub"""
        try:
            cache_key = self._get_cache_key("list_datasets", query, limit)
            cached = self._get_from_cache(cache_key)
            if cached:
                return self._create_response(
                    True, data=cached, latency_ms=0.0, metadata={"cached": True}
                )

            result, latency = await self._execute_with_protection(
                self._list_datasets_api, query, limit
            )

            self._set_cache(cache_key, result)

            return self._create_response(
                success=True,
                data=result,
                latency_ms=latency,
                metadata={"count": len(result)},
            )

        except CircuitBreakerOpenError as e:
            return self._create_response(False, error=str(e))
        except Exception as e:
            logger.error(f"Dataset listing failed: {e}")
            return self._create_response(False, error=str(e))

    async def _list_datasets_api(self, query: str, limit: int) -> List[Dict]:
        """Make API call to list datasets"""
        session = await self._get_session()

        params = {"search": query, "limit": limit}

        try:
            async with session.get(
                f"{self.base_url}/datasets", headers=self.headers, params=params
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid HuggingFace API token")

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            raise TimeoutError(f"Request failed: {e}")

    async def health_check(self) -> ConnectorResponse:
        """Check HuggingFace API health"""
        try:
            result = await self.search_models(query="bert", limit=1)
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
