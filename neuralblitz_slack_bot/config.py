"""
Configuration module for NeuralBlitz Slack Bot
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class SlackBotConfig:
    """Configuration for Slack Bot."""

    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str
    default_channel: Optional[str] = None
    enable_socket_mode: bool = True
    enable_realtime_updates: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "SlackBotConfig":
        """Load configuration from environment variables."""
        return cls(
            slack_bot_token=os.environ.get("SLACK_BOT_TOKEN", ""),
            slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
            slack_app_token=os.environ.get("SLACK_APP_TOKEN", ""),
            default_channel=os.environ.get("DEFAULT_CHANNEL"),
            enable_socket_mode=os.environ.get("ENABLE_SOCKET_MODE", "true").lower()
            == "true",
            enable_realtime_updates=os.environ.get(
                "ENABLE_REALTIME_UPDATES", "true"
            ).lower()
            == "true",
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> bool:
        """Validate that all required configuration is present."""
        return all(
            [self.slack_bot_token, self.slack_signing_secret, self.slack_app_token]
        )


@dataclass
class NeuralBlitzConfig:
    """Configuration for NeuralBlitz integration."""

    api_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "NeuralBlitzConfig":
        """Load configuration from environment variables."""
        return cls(
            api_url=os.environ.get("NEURALBLITZ_API_URL", "http://localhost:8000"),
            api_key=os.environ.get("NEURALBLITZ_API_KEY"),
            timeout=int(os.environ.get("NEURALBLITZ_TIMEOUT", "30")),
            max_retries=int(os.environ.get("NEURALBLITZ_MAX_RETRIES", "3")),
        )
