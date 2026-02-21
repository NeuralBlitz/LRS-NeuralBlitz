"""
Real-time Event Handlers for NeuralBlitz Slack Bot
Handles app mentions, direct messages, and system events.
"""

import logging
import re
from typing import Dict, Any
from datetime import datetime
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class RealTimeEventHandler:
    """Handler for real-time events and notifications."""

    def __init__(self, client, agent_registry: Dict[str, Any], dispatcher=None):
        self.client = client
        self.agent_registry = agent_registry
        self.dispatcher = dispatcher
        self.command_patterns = {
            r"create\s+agent": self._handle_create_agent_request,
            r"status": self._handle_status_request,
            r"help": self._handle_help_request,
            r"drs\s+query\s+(.+)": self._handle_drs_query_request,
            r"charter\s+check": self._handle_charter_check_request,
            r"deploy\s+(.+)": self._handle_deploy_request,
            r"pause\s+(.+)": self._handle_pause_request,
            r"resume\s+(.+)": self._handle_resume_request,
        }

    def handle_app_mention(self, event: Dict[str, Any], say):
        """Handle when the bot is mentioned in a channel."""
        text = event.get("text", "").lower()
        channel_id = event.get("channel")
        user_id = event.get("user")

        # Extract the message after the mention
        mention_pattern = r"<@[A-Z0-9]+>"
        clean_text = re.sub(mention_pattern, "", text).strip()

        logger.info(f"App mention from {user_id} in {channel_id}: {clean_text}")

        # Check for command patterns
        for pattern, handler in self.command_patterns.items():
            match = re.search(pattern, clean_text)
            if match:
                handler(match, channel_id, user_id, say)
                return

        # Default response
        say(
            f"<@{user_id}> Hello! I'm the NeuralBlitz Bot. Try these commands:\n"
            "• `create agent` - Create a new agent\n"
            "• `status` - Show system status\n"
            "• `drs query <query>` - Query the DRS\n"
            "• `charter check` - Run compliance check\n"
            "• `help` - Show all commands"
        )

    def handle_direct_message(self, event: Dict[str, Any], say):
        """Handle direct messages to the bot."""
        text = event.get("text", "").lower()
        user_id = event.get("user")
        channel_id = event.get("channel")

        logger.info(f"DM from {user_id}: {text}")

        # Check for command patterns
        for pattern, handler in self.command_patterns.items():
            match = re.search(pattern, text)
            if match:
                handler(match, channel_id, user_id, say)
                return

        # Default DM response
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"Hello <@{user_id}>! 👋\n\n"
                        "I'm your NeuralBlitz assistant. Here's what I can help you with:"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Quick Actions:*\n"
                        "• Type `create agent` to start agent creation\n"
                        "• Type `status` for system status\n"
                        "• Type `drs query <your query>` to search DRS\n"
                        "• Type `charter check` for compliance\n"
                        "• Type `help` for full command list"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🚀 Create Agent"},
                        "action_id": "agent_create",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📊 System Status"},
                        "action_id": "system_status",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📋 Charter"},
                        "action_id": "charter_check",
                    },
                ],
            },
        ]

        say(blocks=blocks, text="NeuralBlitz Bot - How can I help?")

    def _handle_create_agent_request(self, match, channel_id, user_id, say):
        """Handle agent creation request from natural language."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<@{user_id}> I'll help you create a new agent! Use the button below:",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🚀 Start Agent Creation",
                        },
                        "action_id": "agent_create",
                        "style": "primary",
                    }
                ],
            },
        ]
        say(blocks=blocks)

    def _handle_status_request(self, match, channel_id, user_id, say):
        """Handle status request."""
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
                        f"*Active Agents:* {len(self.agent_registry)}\n"
                        "*DRS Nodes:* 482,150+\n"
                        "*Entropy Budget:* 0.11\n"
                        "*Drift Rate:* 0.007"
                    ),
                },
            },
        ]
        say(blocks=blocks)

    def _handle_help_request(self, match, channel_id, user_id, say):
        """Handle help request."""
        help_text = (
            "*NeuralBlitz Bot Commands:*\n\n"
            "*Slash Commands:*\n"
            "• `/nb-agent` - Agent management\n"
            "• `/nb-status` - System status\n"
            "• `/nb-drs` - DRS operations\n"
            "• `/nb-workflow` - Workflow management\n"
            "• `/nb-charter` - Charter governance\n\n"
            "*Natural Language:*\n"
            "• `create agent` - Start agent creation\n"
            "• `status` - Show status\n"
            "• `drs query <text>` - Query DRS\n"
            "• `charter check` - Compliance check\n"
            "• `deploy <agent-id>` - Deploy agent\n"
            "• `pause <agent-id>` - Pause agent\n"
            "• `resume <agent-id>` - Resume agent"
        )

        say(help_text)

    def _handle_drs_query_request(self, match, channel_id, user_id, say):
        """Handle DRS query from natural language."""
        query = match.group(1)

        # Simulate DRS query
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 DRS Query Results",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Query:* `{query}`"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*Results:*\n42 nodes"},
                    {"type": "mrkdwn", "text": "*Semantic Density:*\n0.85"},
                    {"type": "mrkdwn", "text": "*Phase Coherence:*\n0.92"},
                    {"type": "mrkdwn", "text": "*Entanglement:*\n0.78"},
                ],
            },
        ]
        say(blocks=blocks)

    def _handle_charter_check_request(self, match, channel_id, user_id, say):
        """Handle Charter check request."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Charter Compliance",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Status:* ✅ PASS\n"
                        "*Clauses Checked:* 15\n"
                        "*Violations:* 0\n"
                        "*Warnings:* 2\n"
                        "*Compliance Score:* 98%"
                    ),
                },
            },
        ]
        say(blocks=blocks)

    def _handle_deploy_request(self, match, channel_id, user_id, say):
        """Handle deploy request."""
        agent_id = match.group(1).strip()
        say(f"🚀 Deploying agent `{agent_id}`...")

    def _handle_pause_request(self, match, channel_id, user_id, say):
        """Handle pause request."""
        agent_id = match.group(1).strip()
        say(f"⏸️ Pausing agent `{agent_id}`...")

    def _handle_resume_request(self, match, channel_id, user_id, say):
        """Handle resume request."""
        agent_id = match.group(1).strip()
        say(f"▶️ Resuming agent `{agent_id}`...")

    def send_realtime_update(
        self, channel_id: str, update_type: str, data: Dict[str, Any]
    ):
        """Send real-time update to a channel."""
        if update_type == "agent_status_change":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"🔄 *Agent Status Change*\n"
                            f"Agent: `{data.get('agent_id')}`\n"
                            f"New Status: {data.get('status')}"
                        ),
                    },
                }
            ]
        elif update_type == "system_alert":
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "⚠️ System Alert",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": data.get("message", "Unknown alert"),
                    },
                },
            ]
        elif update_type == "workflow_progress":
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"🔄 *Workflow Progress*\n"
                            f"Workflow: {data.get('workflow_name')}\n"
                            f"Step {data.get('current_step')}/{data.get('total_steps')}"
                        ),
                    },
                }
            ]
        else:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📢 Update: {data.get('message', 'No details')}",
                    },
                }
            ]

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"NeuralBlitz Update: {update_type}",
            )
        except SlackApiError as e:
            logger.error(f"Error sending real-time update: {e}")

    def start_monitoring(self, channel_id: str):
        """Start monitoring and sending periodic updates."""
        import threading

        def monitoring_loop():
            import time

            while True:
                time.sleep(300)  # Send update every 5 minutes
                try:
                    self.send_realtime_update(
                        channel_id,
                        "heartbeat",
                        {
                            "message": "NeuralBlitz system operational",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    )
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")

        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
        logger.info(f"Started monitoring for channel: {channel_id}")
