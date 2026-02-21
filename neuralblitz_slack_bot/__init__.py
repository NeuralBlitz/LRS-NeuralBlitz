"""
NeuralBlitz Slack Bot
A comprehensive Slack integration for NeuralBlitz v20
"""

__version__ = "1.0.0"
__author__ = "NeuralBlitz Team"

from .bot import NeuralBlitzSlackBot, BotConfig
from .command_handlers import (
    AgentCommandHandler,
    DRSCommandHandler,
    CharterCommandHandler,
    WorkflowManager,
    CommandDispatcher,
)
from .interactive_handlers import InteractiveWorkflowHandler
from .event_handlers import RealTimeEventHandler

__all__ = [
    "NeuralBlitzSlackBot",
    "BotConfig",
    "AgentCommandHandler",
    "DRSCommandHandler",
    "CharterCommandHandler",
    "WorkflowManager",
    "CommandDispatcher",
    "InteractiveWorkflowHandler",
    "RealTimeEventHandler",
]
