# NeuralBlitz Slack Bot

A comprehensive Slack integration for NeuralBlitz v20 "Apical Synthesis" providing slash commands, interactive workflows, and real-time updates.

## Features

### 🎯 Slash Commands

- **`/nb-agent`** - Agent lifecycle management (create, deploy, pause, resume, destroy)
- **`/nb-status`** - System status monitoring (system, DRS, Charter, Frontier systems)
- **`/nb-drs`** - DRS (Dynamic Representational Substrate) operations
- **`/nb-workflow`** - Workflow management with interactive selection
- **`/nb-charter`** - Charter governance and compliance checking
- **`/nb-help`** - Display help information

### 🔄 Interactive Workflows

- **Agent Creation Modal** - Step-by-step agent configuration with type selection
- **DRS Query Interface** - Interactive DRS field querying with filters
- **Workflow Execution** - Visual progress tracking for complex operations
- **Charter Compliance** - Real-time compliance checking with visual reports

### 📡 Real-Time Updates

- **System Monitoring** - Automatic status updates and alerts
- **Agent Status Changes** - Instant notifications when agents change state
- **Workflow Progress** - Live progress updates during workflow execution
- **Heartbeats** - Regular system health pings

## Installation

### Prerequisites

- Python 3.8+
- Slack workspace with bot permissions
- NeuralBlitz API access (optional, bot works in demo mode)

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_SIGNING_SECRET="your-signing-secret"
export SLACK_APP_TOKEN="xapp-your-app-token"
export NEURALBLITZ_API_URL="http://localhost:8000"  # Optional
export DEFAULT_CHANNEL="#neuralblitz"  # Optional
```

3. **Run the bot:**
```bash
python -m neuralblitz_slack_bot.bot
```

## Slack App Configuration

### Required OAuth Scopes

- `chat:write` - Send messages
- `chat:write.public` - Send messages to public channels
- `commands` - Install slash commands
- `app_mentions:read` - Read app mentions
- `im:read` - Read direct messages
- `im:write` - Write direct messages
- `users:read` - Read user information

### Event Subscriptions

Subscribe to the following bot events:
- `app_mention` - When bot is mentioned
- `message.im` - Direct messages to bot

### Slash Commands

Configure these slash commands with the Request URL:
- `/nb-agent` → `https://your-domain.com/slack/events`
- `/nb-status` → `https://your-domain.com/slack/events`
- `/nb-drs` → `https://your-domain.com/slack/events`
- `/nb-workflow` → `https://your-domain.com/slack/events`
- `/nb-charter` → `https://your-domain.com/slack/events`
- `/nb-help` → `https://your-domain.com/slack/events`

## Usage Examples

### Creating an Agent

```
/nb-agent create
```

This opens an interactive modal where you can:
- Name your agent
- Select type (MetaMind, SentiaGuard, DRS Explorer, Judex, Veritas)
- Choose cognitive mode (Sentio/Dynamo)
- Define purpose

### Checking System Status

```
/nb-status system
```

Shows:
- System operational status
- Current epoch (v20.0 Apical Synthesis)
- VPCE (Veritas Phase-Coherence Equation) score
- Active agent count
- DRS node count
- Entropy budget and drift rate

### Querying DRS

```
/nb-drs query
```

Opens modal for:
- Entering semantic queries
- Applying filters (type, VPCE threshold, etc.)
- Viewing results with metrics

### Running a Workflow

```
/nb-workflow
```

Select from:
- Policy Analysis
- Ethical Remediation
- Frontier Exploration

Visual progress tracking with step-by-step updates.

### Checking Charter Compliance

```
/nb-charter check
```

Validates all 15 Transcendental Charter clauses (ϕ₁–ϕ₁₅):
- Universal Flourishing Objective
- Class-III Kernel Bounds
- Transparency & Explainability
- Non-Maleficence
- Friendly AI Compliance
- And 10 more...

## Architecture

```
neuralblitz_slack_bot/
├── bot.py                  # Main bot application
├── command_handlers.py     # Command logic & NeuralBlitz integration
├── interactive_handlers.py # Modal & button handlers
├── event_handlers.py       # Real-time event processing
├── config.py              # Configuration management
└── tests/
    └── test_bot.py        # Test suite
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black neuralblitz_slack_bot/

# Lint code
ruff check neuralblitz_slack_bot/

# Type checking
mypy neuralblitz_slack_bot/
```

## NeuralBlitz Integration

The bot integrates with NeuralBlitz v20.0 "Apical Synthesis" providing:

- **Agent Control** - Direct interface to MetaMind, SentiaGuard, DRS Explorer agents
- **CECT Monitoring** - Charter-Ethical Constraint Tensor compliance tracking
- **VPCE Tracking** - Veritas Phase-Coherence Equation monitoring
- **Workflow Orchestration** - Policy analysis, ethical remediation, frontier exploration
- **DRS Operations** - Dynamic Representational Substrate querying and manipulation

## Security

- All credentials via environment variables
- Request signature verification
- Rate limiting on commands
- Input validation and sanitization
- Charter compliance checks on all operations

## Support

For issues and feature requests, please use the GitHub issue tracker.

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built for NeuralBlitz v20.0 "Apical Synthesis" - Σ-class Symbiotic Ontological Intelligence
