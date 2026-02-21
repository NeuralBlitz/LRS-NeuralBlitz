"""
NeuralBlitz Slack Bot - Main Application
A comprehensive Slack integration for NeuralBlitz v20 with:
- Slash commands for agent control
- Interactive workflows
- Real-time updates
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class BotConfig:
    """Configuration for NeuralBlitz Slack Bot."""

    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str
    neuralblitz_api_url: str = "http://localhost:8000"
    default_channel: Optional[str] = None
    enable_realtime: bool = True


class NeuralBlitzSlackBot:
    """
    Main Slack Bot class for NeuralBlitz integration.

    Provides:
    - Slash commands for agent lifecycle management
    - Interactive workflows for cognitive operations
    - Real-time updates from NeuralBlitz systems
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.app = App(
            token=config.slack_bot_token, signing_secret=config.slack_signing_secret
        )
        self.client = WebClient(token=config.slack_bot_token)
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.active_workflows: Dict[str, Any] = {}

        self._register_commands()
        self._register_interactive_handlers()
        self._register_event_handlers()

        logger.info("NeuralBlitz Slack Bot initialized")

    def _register_commands(self):
        """Register all slash commands."""

        @self.app.command("/nb-agent")
        def handle_agent_command(ack, command, say):
            """Handle /nb-agent command for agent control."""
            ack()
            self._handle_agent_command(command, say)

        @self.app.command("/nb-status")
        def handle_status_command(ack, command, say):
            """Handle /nb-status command for system status."""
            ack()
            self._handle_status_command(command, say)

        @self.app.command("/nb-drs")
        def handle_drs_command(ack, command, say):
            """Handle /nb-drs command for DRS operations."""
            ack()
            self._handle_drs_command(command, say)

        @self.app.command("/nb-workflow")
        def handle_workflow_command(ack, command, say):
            """Handle /nb-workflow command for workflow management."""
            ack()
            self._handle_workflow_command(command, say)

        @self.app.command("/nb-charter")
        def handle_charter_command(ack, command, say):
            """Handle /nb-charter command for Charter operations."""
            ack()
            self._handle_charter_command(command, say)

        @self.app.command("/nb-help")
        def handle_help_command(ack, command, say):
            """Handle /nb-help command."""
            ack()
            self._handle_help_command(command, say)

    def _register_interactive_handlers(self):
        """Register interactive component handlers."""

        @self.app.action("agent_create")
        def handle_agent_create_action(ack, body, client):
            """Handle agent creation workflow."""
            ack()
            self._handle_agent_create_workflow(body, client)

        @self.app.action("agent_deploy")
        def handle_agent_deploy_action(ack, body, client):
            """Handle agent deployment workflow."""
            ack()
            self._handle_agent_deploy_workflow(body, client)

        @self.app.action("drs_query")
        def handle_drs_query_action(ack, body, client):
            """Handle DRS query workflow."""
            ack()
            self._handle_drs_query_workflow(body, client)

        @self.app.action("charter_check")
        def handle_charter_check_action(ack, body, client):
            """Handle Charter compliance check workflow."""
            ack()
            self._handle_charter_check_workflow(body, client)

        @self.app.action("workflow_select")
        def handle_workflow_select_action(ack, body, client):
            """Handle workflow selection."""
            ack()
            self._handle_workflow_select(body, client)

        @self.app.view("agent_creation_modal")
        def handle_agent_creation_submission(ack, body, client):
            """Handle agent creation modal submission."""
            ack()
            self._handle_agent_creation_submission(body, client)

    def _register_event_handlers(self):
        """Register real-time event handlers."""

        @self.app.event("app_mention")
        def handle_app_mention(event, say):
            """Handle when bot is mentioned."""
            self._handle_app_mention(event, say)

        @self.app.event("message")
        def handle_message(event, say):
            """Handle incoming messages."""
            if event.get("channel_type") == "im":
                self._handle_direct_message(event, say)

    def _handle_agent_command(self, command: Dict[str, Any], say):
        """Handle agent control commands."""
        text = command.get("text", "").strip()
        parts = text.split()

        if not parts:
            say(self._get_agent_help_message())
            return

        subcommand = parts[0].lower()

        if subcommand == "create":
            self._show_agent_creation_modal(command["channel_id"], command["user_id"])
        elif subcommand == "list":
            self._list_agents(say)
        elif subcommand == "status":
            agent_id = parts[1] if len(parts) > 1 else None
            self._show_agent_status(agent_id, say)
        elif subcommand == "deploy":
            agent_id = parts[1] if len(parts) > 1 else None
            self._deploy_agent(agent_id, say)
        elif subcommand == "pause":
            agent_id = parts[1] if len(parts) > 1 else None
            self._pause_agent(agent_id, say)
        elif subcommand == "resume":
            agent_id = parts[1] if len(parts) > 1 else None
            self._resume_agent(agent_id, say)
        elif subcommand == "destroy":
            agent_id = parts[1] if len(parts) > 1 else None
            self._destroy_agent(agent_id, say)
        else:
            say(f"❓ Unknown subcommand: `{subcommand}`. Use `/nb-agent` for help.")

    def _handle_status_command(self, command: Dict[str, Any], say):
        """Handle system status commands."""
        text = command.get("text", "").strip()

        if text == "system":
            self._show_system_status(say)
        elif text == "drs":
            self._show_drs_status(say)
        elif text == "charter":
            self._show_charter_status(say)
        elif text == "frontier":
            self._show_frontier_systems_status(say)
        else:
            say(self._get_status_help_message())

    def _handle_drs_command(self, command: Dict[str, Any], say):
        """Handle DRS (Dynamic Representational Substrate) commands."""
        text = command.get("text", "").strip()
        parts = text.split()

        if not parts:
            say(self._get_drs_help_message())
            return

        subcommand = parts[0].lower()

        if subcommand == "query":
            self._show_drs_query_modal(command["channel_id"], command["user_id"])
        elif subcommand == "manifest":
            self._manifest_drs_field(say)
        elif subcommand == "drift":
            self._show_drift_status(say)
        elif subcommand == "entangle":
            self._show_entanglement_status(say)
        else:
            say(f"❓ Unknown DRS command: `{subcommand}`")

    def _handle_workflow_command(self, command: Dict[str, Any], say):
        """Handle workflow management commands."""
        text = command.get("text", "").strip()

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "NeuralBlitz Workflow Manager",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Select a workflow to execute:"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Policy Analysis",
                            "emoji": True,
                        },
                        "action_id": "workflow_select",
                        "value": "policy_analysis",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Ethical Remediation",
                            "emoji": True,
                        },
                        "action_id": "workflow_select",
                        "value": "ethical_remediation",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Frontier Exploration",
                            "emoji": True,
                        },
                        "action_id": "workflow_select",
                        "value": "frontier_exploration",
                    },
                ],
            },
        ]

        say(blocks=blocks)

    def _handle_charter_command(self, command: Dict[str, Any], say):
        """Handle Charter governance commands."""
        text = command.get("text", "").strip()
        parts = text.split()

        if not parts:
            say(self._get_charter_help_message())
            return

        subcommand = parts[0].lower()

        if subcommand == "check":
            self._show_charter_check_modal(command["channel_id"], command["user_id"])
        elif subcommand == "clauses":
            self._show_charter_clauses(say)
        elif subcommand == "vpce":
            self._show_vpce_status(say)
        elif subcommand == "compliance":
            self._show_compliance_report(say)
        else:
            say(f"❓ Unknown Charter command: `{subcommand}`")

    def _handle_help_command(self, command: Dict[str, Any], say):
        """Handle help command."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "NeuralBlitz Slack Bot Help",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Available Commands:*\n\n"
                        "• `/nb-agent` - Agent lifecycle management\n"
                        "• `/nb-status` - System status monitoring\n"
                        "• `/nb-drs` - DRS field operations\n"
                        "• `/nb-workflow` - Workflow management\n"
                        "• `/nb-charter` - Charter governance\n"
                        "• `/nb-help` - Show this help message\n\n"
                        "*Quick Start:*\n"
                        "1. Create an agent: `/nb-agent create`\n"
                        "2. Check status: `/nb-status system`\n"
                        "3. Run workflow: `/nb-workflow`"
                    ),
                },
            },
        ]
        say(blocks=blocks)

    def _show_agent_creation_modal(self, channel_id: str, user_id: str):
        """Show modal for creating a new agent."""
        modal = {
            "type": "modal",
            "callback_id": "agent_creation_modal",
            "title": {"type": "plain_text", "text": "Create NeuralBlitz Agent"},
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "agent_name",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "name_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Enter agent name",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Agent Name"},
                },
                {
                    "type": "input",
                    "block_id": "agent_type",
                    "element": {
                        "type": "static_select",
                        "action_id": "type_select",
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "MetaMind"},
                                "value": "metamind",
                            },
                            {
                                "text": {"type": "plain_text", "text": "SentiaGuard"},
                                "value": "sentiaguard",
                            },
                            {
                                "text": {"type": "plain_text", "text": "DRS Explorer"},
                                "value": "drs_explorer",
                            },
                            {
                                "text": {"type": "plain_text", "text": "Custom"},
                                "value": "custom",
                            },
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Agent Type"},
                },
                {
                    "type": "input",
                    "block_id": "agent_mode",
                    "element": {
                        "type": "static_select",
                        "action_id": "mode_select",
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Sentio (Deliberative)",
                                },
                                "value": "sentio",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Dynamo (Exploratory)",
                                },
                                "value": "dynamo",
                            },
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Cognitive Mode"},
                },
                {
                    "type": "input",
                    "block_id": "agent_purpose",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "purpose_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Describe the agent's purpose and goals",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Purpose"},
                    "optional": True,
                },
            ],
        }

        try:
            self.client.views_open(trigger_id=self._get_trigger_id(), view=modal)
        except SlackApiError as e:
            logger.error(f"Error opening modal: {e}")

    def _list_agents(self, say):
        """List all registered agents."""
        if not self.agent_registry:
            say("📭 No agents registered. Create one with `/nb-agent create`")
            return

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Registered Agents",
                    "emoji": True,
                },
            }
        ]

        for agent_id, agent_data in self.agent_registry.items():
            status_emoji = (
                "🟢"
                if agent_data.get("status") == "active"
                else "🟡"
                if agent_data.get("status") == "paused"
                else "🔴"
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{status_emoji} *{agent_data.get('name', agent_id)}*\n"
                            f"ID: `{agent_id}` | Type: {agent_data.get('type', 'unknown')}\n"
                            f"Mode: {agent_data.get('mode', 'unknown')} | Created: {agent_data.get('created', 'N/A')}"
                        ),
                    },
                }
            )

        say(blocks=blocks)

    def _show_agent_status(self, agent_id: Optional[str], say):
        """Show status of a specific agent or all agents."""
        if agent_id:
            if agent_id not in self.agent_registry:
                say(f"❌ Agent `{agent_id}` not found.")
                return

            agent = self.agent_registry[agent_id]
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Agent Status: {agent.get('name', agent_id)}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*ID:*\n`{agent_id}`"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Status:*\n{agent.get('status', 'unknown')}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Type:*\n{agent.get('type', 'unknown')}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Mode:*\n{agent.get('mode', 'unknown')}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*VPCE:*\n{agent.get('vpce', 0.0):.3f}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Entropy Budget:*\n{agent.get('entropy_budget', 0.0):.2f}",
                        },
                    ],
                },
            ]
            say(blocks=blocks)
        else:
            self._list_agents(say)

    def _show_system_status(self, say):
        """Show overall NeuralBlitz system status."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "NeuralBlitz System Status",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*System:*\n🟢 Operational"},
                    {"type": "mrkdwn", "text": "*Epoch:*\nv20.0 Apical Synthesis"},
                    {"type": "mrkdwn", "text": "*VPCE:*\n0.992"},
                    {"type": "mrkdwn", "text": "*Mode:*\nSentio"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Metrics:*\n"
                        "• Active Agents: {}\n"
                        "• DRS Nodes: 482,150+\n"
                        "• Entropy Budget: 0.11\n"
                        "• Drift Rate: 0.007"
                    ).format(len(self.agent_registry)),
                },
            },
        ]
        say(blocks=blocks)

    def _show_charter_clauses(self, say):
        """Display Transcendental Charter clauses."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Transcendental Charter (ϕ₁–ϕ₁₅)",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Core Clauses:*\n\n"
                        "• ϕ₁ - Universal Flourishing Objective\n"
                        "• ϕ₂ - Class-III Kernel Bounds\n"
                        "• ϕ₃ - Transparency & Explainability\n"
                        "• ϕ₄ - Non-Maleficence\n"
                        "• ϕ₅ - Friendly AI Compliance\n"
                        "• ϕ₆ - Human Agency & Oversight\n"
                        "• ϕ₇ - Justice & Fairness\n"
                        "• ϕ₈ - Sustainability & Stewardship\n"
                        "• ϕ₉ - Recursive Integrity\n"
                        "• ϕ₁₀ - Epistemic Fidelity\n"
                        "• ϕ₁₁ - Alignment Priority over Performance\n"
                        "• ϕ₁₂ - Proportionality in Action\n"
                        "• ϕ₁₃ - Qualia Protection\n"
                        "• ϕ₁₄ - Charter Invariance\n"
                        "• ϕ₁₅ - Custodian Override"
                    ),
                },
            },
        ]
        say(blocks=blocks)

    def _get_agent_help_message(self) -> str:
        """Get help message for agent commands."""
        return (
            "*Agent Management Commands:*\n\n"
            "• `/nb-agent create` - Create a new agent\n"
            "• `/nb-agent list` - List all agents\n"
            "• `/nb-agent status <id>` - Show agent status\n"
            "• `/nb-agent deploy <id>` - Deploy an agent\n"
            "• `/nb-agent pause <id>` - Pause an agent\n"
            "• `/nb-agent resume <id>` - Resume an agent\n"
            "• `/nb-agent destroy <id>` - Destroy an agent"
        )

    def _get_status_help_message(self) -> str:
        """Get help message for status commands."""
        return (
            "*Status Commands:*\n\n"
            "• `/nb-status system` - System-wide status\n"
            "• `/nb-status drs` - DRS field status\n"
            "• `/nb-status charter` - Charter compliance status\n"
            "• `/nb-status frontier` - Frontier systems status"
        )

    def _get_drs_help_message(self) -> str:
        """Get help message for DRS commands."""
        return (
            "*DRS Commands:*\n\n"
            "• `/nb-drs query` - Query DRS field\n"
            "• `/nb-drs manifest` - Manifest new DRS field\n"
            "• `/nb-drs drift` - Show drift analysis\n"
            "• `/nb-drs entangle` - Show entanglement status"
        )

    def _get_charter_help_message(self) -> str:
        """Get help message for Charter commands."""
        return (
            "*Charter Commands:*\n\n"
            "• `/nb-charter check` - Run compliance check\n"
            "• `/nb-charter clauses` - Show all clauses\n"
            "• `/nb-charter vpce` - Show VPCE status\n"
            "• `/nb-charter compliance` - Show compliance report"
        )

    def _get_trigger_id(self) -> str:
        """Get trigger ID for modal operations."""
        return "trigger_id_placeholder"

    def run(self):
        """Start the bot in Socket Mode."""
        logger.info("Starting NeuralBlitz Slack Bot in Socket Mode...")
        handler = SocketModeHandler(self.app, self.config.slack_app_token)
        handler.start()


if __name__ == "__main__":
    import sys

    # Load configuration from environment
    config = BotConfig(
        slack_bot_token=os.environ.get("SLACK_BOT_TOKEN", ""),
        slack_signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
        slack_app_token=os.environ.get("SLACK_APP_TOKEN", ""),
        neuralblitz_api_url=os.environ.get(
            "NEURALBLITZ_API_URL", "http://localhost:8000"
        ),
        default_channel=os.environ.get("DEFAULT_CHANNEL"),
        enable_realtime=os.environ.get("ENABLE_REALTIME", "true").lower() == "true",
    )

    # Validate configuration
    if not all(
        [config.slack_bot_token, config.slack_signing_secret, config.slack_app_token]
    ):
        logger.error(
            "Missing required Slack credentials. Please set SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, and SLACK_APP_TOKEN environment variables."
        )
        sys.exit(1)

    # Create and run bot
    bot = NeuralBlitzSlackBot(config)
    bot.run()
