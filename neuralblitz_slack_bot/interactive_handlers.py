"""
Interactive Workflow Handlers for NeuralBlitz Slack Bot
Handles modal submissions, button clicks, and interactive components.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from slack_sdk.errors import SlackApiError

from .command_handlers import CommandDispatcher

logger = logging.getLogger(__name__)


class InteractiveWorkflowHandler:
    """Handler for interactive workflows and modals."""

    def __init__(self, client, dispatcher: CommandDispatcher):
        self.client = client
        self.dispatcher = dispatcher

    def handle_agent_create_workflow(self, body: Dict[str, Any]):
        """Handle agent creation workflow."""
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]

        # Open agent creation modal
        modal_view = {
            "type": "modal",
            "callback_id": "agent_creation_modal",
            "title": {"type": "plain_text", "text": "Create NeuralBlitz Agent"},
            "submit": {"type": "plain_text", "text": "Create Agent"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Create a new agent for the NeuralBlitz system.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "block_id": "agent_name_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "agent_name_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., MetaMind-Explorer-01",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Agent Name"},
                },
                {
                    "type": "input",
                    "block_id": "agent_type_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "agent_type_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select agent type",
                        },
                        "options": [
                            {
                                "text": {"type": "plain_text", "text": "🧠 MetaMind"},
                                "value": "metamind",
                            },
                            {
                                "text": {"type": "plain_text", "text": "🛡️ SentiaGuard"},
                                "value": "sentiaguard",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "📊 DRS Explorer",
                                },
                                "value": "drs_explorer",
                            },
                            {
                                "text": {"type": "plain_text", "text": "⚖️ Judex"},
                                "value": "judex",
                            },
                            {
                                "text": {"type": "plain_text", "text": "🔮 Veritas"},
                                "value": "veritas",
                            },
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Agent Type"},
                },
                {
                    "type": "input",
                    "block_id": "agent_mode_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "agent_mode_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select cognitive mode",
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔍 Sentio (Deliberative)",
                                },
                                "value": "sentio",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "⚡ Dynamo (Exploratory)",
                                },
                                "value": "dynamo",
                            },
                        ],
                    },
                    "label": {"type": "plain_text", "text": "Cognitive Mode"},
                },
                {
                    "type": "input",
                    "block_id": "agent_purpose_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "agent_purpose_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Describe the agent's purpose and goals...",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Purpose (Optional)"},
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "ℹ️ Agents operate under the Transcendental Charter (ϕ₁–ϕ₁₅)",
                        }
                    ],
                },
            ],
        }

        try:
            self.client.views_open(trigger_id=body["trigger_id"], view=modal_view)
        except SlackApiError as e:
            logger.error(f"Error opening agent creation modal: {e}")

    def handle_agent_creation_submission(self, body: Dict[str, Any]):
        """Handle agent creation modal submission."""
        values = body["view"]["state"]["values"]

        # Extract values from modal
        name = values["agent_name_block"]["agent_name_input"]["value"]
        agent_type = values["agent_type_block"]["agent_type_select"]["selected_option"][
            "value"
        ]
        mode = values["agent_mode_block"]["agent_mode_select"]["selected_option"][
            "value"
        ]
        purpose = (
            values.get("agent_purpose_block", {})
            .get("agent_purpose_input", {})
            .get("value", "")
        )

        # Create agent
        agent_data = self.dispatcher.dispatch_agent_create(
            name, agent_type, mode, purpose
        )

        # Send confirmation message
        channel_id = body["user"]["id"]  # DM the user

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Agent Created Successfully",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Name:*\n{agent_data['name']}"},
                    {"type": "mrkdwn", "text": f"*ID:*\n`{agent_data['id']}`"},
                    {"type": "mrkdwn", "text": f"*Type:*\n{agent_data['type']}"},
                    {"type": "mrkdwn", "text": f"*Mode:*\n{agent_data['mode']}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Purpose:*\n{agent_data.get('purpose', 'N/A')}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🚀 Deploy Agent",
                            "emoji": True,
                        },
                        "action_id": "agent_deploy",
                        "value": agent_data["id"],
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 View Status",
                            "emoji": True,
                        },
                        "action_id": "agent_status",
                        "value": agent_data["id"],
                    },
                ],
            },
        ]

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Agent {agent_data['name']} created successfully",
            )
        except SlackApiError as e:
            logger.error(f"Error sending confirmation: {e}")

    def handle_agent_deploy_workflow(self, body: Dict[str, Any]):
        """Handle agent deployment workflow."""
        agent_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]

        success = self.dispatcher.dispatch_agent_deploy(agent_id)

        if success:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Agent `{agent_id}` deployed successfully!",
                    },
                }
            ]
        else:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ Failed to deploy agent `{agent_id}`. Agent not found.",
                    },
                }
            ]

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Agent deployment {'successful' if success else 'failed'}",
            )
        except SlackApiError as e:
            logger.error(f"Error sending deployment confirmation: {e}")

    def handle_drs_query_workflow(self, body: Dict[str, Any]):
        """Handle DRS query workflow."""
        modal_view = {
            "type": "modal",
            "callback_id": "drs_query_modal",
            "title": {"type": "plain_text", "text": "Query DRS Field"},
            "submit": {"type": "plain_text", "text": "Query"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "query_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "query_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Enter your DRS query...",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Query"},
                },
                {
                    "type": "input",
                    "block_id": "filters_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "filters_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., type:concept, vpce_min:0.95",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Filters (Optional)"},
                },
            ],
        }

        try:
            self.client.views_open(trigger_id=body["trigger_id"], view=modal_view)
        except SlackApiError as e:
            logger.error(f"Error opening DRS query modal: {e}")

    def handle_charter_check_workflow(self, body: Dict[str, Any]):
        """Handle Charter compliance check workflow."""
        channel_id = body["channel"]["id"]

        # Run compliance check
        results = self.dispatcher.dispatch_charter_check("all")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Charter Compliance Check",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{'✅ PASS' if results['overall_status'] == 'PASS' else '❌ FAIL'}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Clauses Checked:*\n{results['clauses_checked']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Violations:*\n{len(results['violations'])}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Warnings:*\n{len(results['warnings'])}",
                    },
                ],
            },
        ]

        if results["warnings"]:
            warning_text = "\n".join(
                [
                    f"• {w['clause']}: {w['message']} (stress: {w['stress']:.2f})"
                    for w in results["warnings"]
                ]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Warnings:*\n{warning_text}"},
                }
            )

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Charter compliance check: {results['overall_status']}",
            )
        except SlackApiError as e:
            logger.error(f"Error sending compliance results: {e}")

    def handle_workflow_select(self, body: Dict[str, Any]):
        """Handle workflow selection."""
        workflow_type = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]

        # Start workflow
        workflow_data = self.dispatcher.dispatch_workflow_start(
            workflow_type, user_id, channel_id
        )

        if not workflow_data:
            try:
                self.client.chat_postMessage(
                    channel=channel_id,
                    text="❌ Failed to start workflow. Please try again.",
                )
            except SlackApiError as e:
                logger.error(f"Error sending workflow error: {e}")
            return

        # Send workflow started message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔄 Workflow Started: {workflow_data['name']}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Workflow ID:* `{workflow_data['id']}`\n*Status:* {workflow_data['status']}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Steps:*\n"
                    + "\n".join(
                        [
                            f"{'⏳' if i == workflow_data['current_step'] else '✅' if i < workflow_data['current_step'] else '⬜'} {i + 1}. {step}"
                            for i, step in enumerate(workflow_data["steps"])
                        ]
                    ),
                },
            },
        ]

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Workflow {workflow_data['name']} started",
            )
        except SlackApiError as e:
            logger.error(f"Error sending workflow start message: {e}")

        # Simulate workflow execution (in real implementation, this would be async)
        self._simulate_workflow_execution(workflow_data, channel_id)

    def _simulate_workflow_execution(
        self, workflow_data: Dict[str, Any], channel_id: str
    ):
        """Simulate workflow execution with progress updates."""
        import time

        for i in range(len(workflow_data["steps"])):
            time.sleep(2)  # Simulate step execution

            workflow_data["current_step"] = i + 1

            # Update progress
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔄 Workflow Progress: {workflow_data['name']}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Workflow ID:* `{workflow_data['id']}`",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Steps:*\n"
                        + "\n".join(
                            [
                                f"{'⏳' if j == workflow_data['current_step'] - 1 else '✅' if j < workflow_data['current_step'] - 1 else '⬜'} {j + 1}. {step}"
                                for j, step in enumerate(workflow_data["steps"])
                            ]
                        ),
                    },
                },
            ]

            try:
                self.client.chat_postMessage(
                    channel=channel_id,
                    blocks=blocks,
                    text=f"Workflow progress: Step {i + 1}/{len(workflow_data['steps'])}",
                )
            except SlackApiError as e:
                logger.error(f"Error sending workflow progress: {e}")

        # Send completion message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"✅ Workflow Complete: {workflow_data['name']}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Workflow ID:* `{workflow_data['id']}`\n*Completed:* {datetime.utcnow().isoformat()}",
                },
            },
        ]

        try:
            self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=f"Workflow {workflow_data['name']} completed",
            )
        except SlackApiError as e:
            logger.error(f"Error sending workflow completion: {e}")
