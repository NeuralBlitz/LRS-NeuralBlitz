"""
IoT Device Mesh Integration System - Automation Rules Engine
============================================================
Smart home automation rules engine with condition evaluation,
action execution, and scheduling capabilities.

Author: NeuralBlitz Systems
Version: 2.0.0
"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from collections import deque
import uuid

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of automation triggers."""

    DEVICE_STATE_CHANGE = auto()
    DEVICE_ATTRIBUTE_CHANGE = auto()
    TIME_SCHEDULED = auto()
    SUNRISE = auto()
    SUNSET = auto()
    MANUAL = auto()
    WEBHOOK = auto()
    SCENE_ACTIVATED = auto()
    DEVICE_ONLINE = auto()
    DEVICE_OFFLINE = auto()


class ConditionOperator(Enum):
    """Comparison operators for conditions."""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUALS = ">="
    LESS_EQUALS = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    CHANGED = "changed"
    BEFORE = "before"
    AFTER = "after"


class ActionType(Enum):
    """Types of automation actions."""

    DEVICE_COMMAND = auto()
    DELAY = auto()
    SCENE_ACTIVATE = auto()
    NOTIFICATION = auto()
    WEBHOOK_CALL = auto()
    SET_VARIABLE = auto()
    LOG_MESSAGE = auto()
    CONDITIONAL = auto()
    STOP_AUTOMATION = auto()


@dataclass
class Trigger:
    """Automation trigger definition."""

    trigger_type: TriggerType
    device_id: str = ""
    attribute: str = ""
    value: Any = None
    operator: ConditionOperator = ConditionOperator.EQUALS
    time_expression: str = ""  # For scheduled triggers
    offset_minutes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        op = (
            self.operator.value
            if hasattr(self.operator, "value")
            else str(self.operator)
        )
        tt = (
            self.trigger_type.name
            if hasattr(self.trigger_type, "name")
            else str(self.trigger_type)
        )
        return {
            "type": tt,
            "device_id": self.device_id,
            "attribute": self.attribute,
            "value": self.value,
            "operator": op,
            "time_expression": self.time_expression,
            "offset_minutes": self.offset_minutes,
        }


@dataclass
class Condition:
    """Automation condition definition."""

    device_id: str = ""
    attribute: str = ""
    value: Any = None
    operator: ConditionOperator = ConditionOperator.EQUALS
    operator_value: Any = None  # For range comparisons

    def to_dict(self) -> Dict[str, Any]:
        op = (
            self.operator.value
            if hasattr(self.operator, "value")
            else str(self.operator)
        )
        return {
            "device_id": self.device_id,
            "attribute": self.attribute,
            "value": self.value,
            "operator": op,
            "operator_value": self.operator_value,
        }


@dataclass
class Action:
    """Automation action definition."""

    action_type: ActionType
    device_id: str = ""
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    delay_seconds: float = 0
    scene_name: str = ""
    message: str = ""
    webhook_url: str = ""
    variable_name: str = ""
    variable_value: Any = None
    log_level: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        at = (
            self.action_type.value
            if hasattr(self.action_type, "value")
            else str(self.action_type)
        )
        return {
            "type": at,
            "device_id": self.device_id,
            "command": self.command,
            "params": self.params,
            "delay_seconds": self.delay_seconds,
            "scene_name": self.scene_name,
            "message": self.message,
            "webhook_url": self.webhook_url,
            "variable_name": self.variable_name,
            "variable_value": self.variable_value,
            "log_level": self.log_level,
        }


@dataclass
class AutomationRule:
    """Complete automation rule."""

    rule_id: str
    name: str
    description: str = ""
    enabled: bool = True
    triggers: List[Trigger] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    priority: int = 0
    max_executions: int = 0  # 0 = unlimited
    execution_count: int = 0
    cooldown_seconds: float = 0
    last_executed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "triggers": [t.to_dict() for t in self.triggers],
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "priority": self.priority,
            "max_executions": self.max_executions,
            "execution_count": self.execution_count,
            "cooldown_seconds": self.cooldown_seconds,
            "last_executed": self.last_executed.isoformat()
            if self.last_executed
            else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }


class ConditionEvaluator:
    """Evaluates automation conditions against device states."""

    def __init__(self, device_state_getter: Callable[[str, str], Any]):
        self.get_device_state = device_state_getter

    def evaluate(self, condition: Condition) -> bool:
        """Evaluate a single condition."""
        try:
            # Get device attribute value
            device_value = self.get_device_state(
                condition.device_id, condition.attribute
            )

            # Handle special operators
            if condition.operator == ConditionOperator.CHANGED:
                return True  # Changed is handled by trigger

            # Compare values
            return self._compare(
                device_value,
                condition.value,
                condition.operator,
                condition.operator_value,
            )

        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False

    def _compare(
        self,
        actual: Any,
        expected: Any,
        operator: ConditionOperator,
        operator_value: Any = None,
    ) -> bool:
        """Compare actual and expected values."""

        # Handle None values
        if actual is None:
            return expected is None

        # Convert to comparable types
        try:
            if isinstance(expected, str) and expected.lower() in ["true", "false"]:
                expected = expected.lower() == "true"
            if isinstance(actual, str) and actual.lower() in ["true", "false"]:
                actual = actual.lower() == "true"
        except:
            pass

        # Perform comparison
        if operator == ConditionOperator.EQUALS:
            return actual == expected
        elif operator == ConditionOperator.NOT_EQUALS:
            return actual != expected
        elif operator == ConditionOperator.GREATER_THAN:
            return float(actual) > float(expected)
        elif operator == ConditionOperator.LESS_THAN:
            return float(actual) < float(expected)
        elif operator == ConditionOperator.GREATER_EQUALS:
            return float(actual) >= float(expected)
        elif operator == ConditionOperator.LESS_EQUALS:
            return float(actual) <= float(expected)
        elif operator == ConditionOperator.CONTAINS:
            return str(expected) in str(actual)
        elif operator == ConditionOperator.NOT_CONTAINS:
            return str(expected) not in str(actual)
        elif operator == ConditionOperator.IN:
            return actual in (expected if isinstance(expected, list) else [expected])
        elif operator == ConditionOperator.NOT_IN:
            return actual not in (
                expected if isinstance(expected, list) else [expected]
            )

        return False


class ActionExecutor:
    """Executes automation actions."""

    def __init__(
        self,
        device_command_sender: Callable[[str, str, Dict], bool],
        scene_activator: Callable[[str], bool],
        notification_sender: Callable[[str, str], None] = None,
        webhook_caller: Callable[[str, Dict], None] = None,
    ):
        self.send_device_command = device_command_sender
        self.activate_scene = scene_activator
        self.send_notification = notification_sender or (lambda x, y: None)
        self.call_webhook = webhook_caller or (lambda x, y: None)

        self._variables: Dict[str, Any] = {}

    def execute(self, action: Action) -> bool:
        """Execute a single action."""
        try:
            logger.debug(f"Executing action: {action.action_type.name}")

            if action.action_type == ActionType.DEVICE_COMMAND:
                return self._execute_device_command(action)
            elif action.action_type == ActionType.DELAY:
                time.sleep(action.delay_seconds)
                return True
            elif action.action_type == ActionType.SCENE_ACTIVATE:
                return self.activate_scene(action.scene_name)
            elif action.action_type == ActionType.NOTIFICATION:
                self.send_notification(action.message, action.device_id)
                return True
            elif action.action_type == ActionType.WEBHOOK_CALL:
                self.call_webhook(action.webhook_url, action.params)
                return True
            elif action.action_type == ActionType.SET_VARIABLE:
                self._variables[action.variable_name] = action.variable_value
                return True
            elif action.action_type == ActionType.LOG_MESSAGE:
                self._log_message(action)
                return True
            elif action.action_type == ActionType.CONDITIONAL:
                return True  # Handled by rule engine
            else:
                logger.warning(f"Unknown action type: {action.action_type}")
                return False

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return False

    def _execute_device_command(self, action: Action) -> bool:
        """Execute a device command."""
        return self.send_device_command(action.device_id, action.command, action.params)

    def _log_message(self, action: Action):
        """Log a message."""
        level = action.log_level.upper()
        message = f"[Automation] {action.message}"

        if level == "DEBUG":
            logger.debug(message)
        elif level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        else:
            logger.info(message)

    def get_variable(self, name: str) -> Any:
        """Get a variable value."""
        return self._variables.get(name)

    def set_variable(self, name: str, value: Any):
        """Set a variable value."""
        self._variables[name] = value


class AutomationRuleEngine:
    """
    Core automation rules engine.
    Manages rules, triggers, conditions, and actions.
    """

    def __init__(self):
        self._rules: Dict[str, AutomationRule] = {}
        self._device_state: Dict[str, Dict[str, Any]] = {}
        self._execution_history: deque = deque(maxlen=1000)
        self._running = False

        # Callbacks
        self._device_state_getter: Optional[Callable[[str, str], Any]] = None
        self._device_command_sender: Optional[Callable[[str, str, Dict], bool]] = None
        self._scene_activator: Optional[Callable[[str], bool]] = None
        self._notification_sender: Optional[Callable[[str, str], None]] = None

        self._condition_evaluator: Optional[ConditionEvaluator] = None
        self._action_executor: Optional[ActionExecutor] = None

        self._lock = threading.RLock()

        logger.info("Automation Rule Engine initialized")

    def configure(
        self,
        device_state_getter: Callable[[str, str], Any],
        device_command_sender: Callable[[str, str, Dict], bool],
        scene_activator: Callable[[str], bool],
        notification_sender: Callable[[str, str], None] = None,
    ):
        """Configure the rule engine with dependencies."""
        self._device_state_getter = device_state_getter
        self._device_command_sender = device_command_sender
        self._scene_activator = scene_activator
        self._notification_sender = notification_sender

        self._condition_evaluator = ConditionEvaluator(device_state_getter)
        self._action_executor = ActionExecutor(
            device_command_sender, scene_activator, notification_sender
        )

        logger.info("Automation Rule Engine configured")

    def start(self):
        """Start the rule engine."""
        self._running = True
        logger.info("Automation Rule Engine started")

    def stop(self):
        """Stop the rule engine."""
        self._running = False
        logger.info("Automation Rule Engine stopped")

    def add_rule(self, rule: AutomationRule):
        """Add an automation rule."""
        with self._lock:
            self._rules[rule.rule_id] = rule
            logger.info(f"Rule added: {rule.name} ({rule.rule_id})")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an automation rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                logger.info(f"Rule removed: {rule_id}")
                return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AutomationRule]:
        """Get all rules."""
        return list(self._rules.values())

    def get_enabled_rules(self) -> List[AutomationRule]:
        """Get all enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            logger.info(f"Rule enabled: {rule_id}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            logger.info(f"Rule disabled: {rule_id}")
            return True
        return False

    def update_device_state(self, device_id: str, state: Dict[str, Any]):
        """Update device state and check for trigger matches."""
        with self._lock:
            old_state = self._device_state.get(device_id, {}).copy()
            self._device_state[device_id] = state.copy()

        # Check for state changes that might trigger rules
        self._check_state_change_triggers(device_id, old_state, state)

    def _check_state_change_triggers(
        self, device_id: str, old_state: Dict[str, Any], new_state: Dict[str, Any]
    ):
        """Check if any state changes match triggers."""

        with self._lock:
            matching_rules = []

            for rule in self._rules.values():
                if not rule.enabled:
                    continue

                for trigger in rule.triggers:
                    if trigger.trigger_type == TriggerType.DEVICE_STATE_CHANGE:
                        if trigger.device_id == device_id:
                            # Check if condition matches
                            if self._evaluate_rule_conditions(rule):
                                matching_rules.append(rule)
                                break

        # Execute matching rules
        for rule in matching_rules:
            self._execute_rule(
                rule, {"trigger_type": "state_change", "device_id": device_id}
            )

    def trigger_rule(self, rule_id: str, context: Dict[str, Any] = None):
        """Manually trigger a rule."""
        rule = self._rules.get(rule_id)
        if rule and rule.enabled:
            self._execute_rule(rule, context or {"trigger_type": "manual"})
        else:
            logger.warning(f"Rule not found or disabled: {rule_id}")

    def _evaluate_rule_conditions(self, rule: AutomationRule) -> bool:
        """Evaluate all conditions of a rule."""
        if not rule.conditions:
            return True  # No conditions = always run

        if not self._condition_evaluator:
            logger.error("Condition evaluator not configured")
            return False

        for condition in rule.conditions:
            if not self._condition_evaluator.evaluate(condition):
                return False

        return True

    def _execute_rule(self, rule: AutomationRule, context: Dict[str, Any]):
        """Execute a rule's actions."""

        # Check cooldown
        if rule.cooldown_seconds > 0 and rule.last_executed:
            elapsed = (datetime.now() - rule.last_executed).total_seconds()
            if elapsed < rule.cooldown_seconds:
                logger.debug(f"Rule {rule.name} in cooldown, skipping")
                return

        # Check execution limit
        if rule.max_executions > 0 and rule.execution_count >= rule.max_executions:
            logger.info(f"Rule {rule.name} reached execution limit")
            return

        logger.info(f"Executing rule: {rule.name}")

        # Execute actions
        if self._action_executor:
            for action in rule.actions:
                self._action_executor.execute(action)

        # Update rule stats
        rule.execution_count += 1
        rule.last_executed = datetime.now()

        # Record execution
        self._execution_history.append(
            {
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "executed_at": datetime.now().isoformat(),
                "context": context,
            }
        )

    def get_execution_history(
        self, rule_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get execution history."""
        history = list(self._execution_history)

        if rule_id:
            history = [h for h in history if h["rule_id"] == rule_id]

        return history[-limit:]

    def export_rules(self) -> str:
        """Export all rules as JSON."""
        rules_data = [rule.to_dict() for rule in self._rules.values()]
        return json.dumps(rules_data, indent=2)

    def import_rules(self, rules_json: str) -> int:
        """Import rules from JSON."""
        try:
            rules_data = json.loads(rules_json)
            imported = 0

            for rule_data in rules_data:
                rule = self._parse_rule_from_dict(rule_data)
                self.add_rule(rule)
                imported += 1

            return imported

        except json.JSONDecodeError as e:
            logger.error(f"Failed to import rules: {e}")
            return 0

    def _parse_rule_from_dict(self, data: Dict[str, Any]) -> AutomationRule:
        """Parse AutomationRule from dictionary."""
        triggers = [
            Trigger(
                trigger_type=TriggerType[t["type"]],
                device_id=t.get("device_id", ""),
                attribute=t.get("attribute", ""),
                value=t.get("value"),
                operator=ConditionOperator(t.get("operator", "==")),
                time_expression=t.get("time_expression", ""),
                offset_minutes=t.get("offset_minutes", 0),
            )
            for t in data.get("triggers", [])
        ]

        conditions = [
            Condition(
                device_id=c.get("device_id", ""),
                attribute=c.get("attribute", ""),
                value=c.get("value"),
                operator=ConditionOperator(c.get("operator", "==")),
                operator_value=c.get("operator_value"),
            )
            for c in data.get("conditions", [])
        ]

        actions = [
            Action(
                action_type=ActionType[a["type"]],
                device_id=a.get("device_id", ""),
                command=a.get("command", ""),
                params=a.get("params", {}),
                delay_seconds=a.get("delay_seconds", 0),
                scene_name=a.get("scene_name", ""),
                message=a.get("message", ""),
                webhook_url=a.get("webhook_url", ""),
                variable_name=a.get("variable_name", ""),
                variable_value=a.get("variable_value"),
                log_level=a.get("log_level", "INFO"),
            )
            for a in data.get("actions", [])
        ]

        return AutomationRule(
            rule_id=data.get("rule_id", str(uuid.uuid4())),
            name=data.get("name", "Imported Rule"),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            triggers=triggers,
            conditions=conditions,
            actions=actions,
            priority=data.get("priority", 0),
            max_executions=data.get("max_executions", 0),
            cooldown_seconds=data.get("cooldown_seconds", 0),
            tags=data.get("tags", []),
        )


class SceneManager:
    """Manages automation scenes (predefined action sets)."""

    def __init__(self, action_executor: ActionExecutor):
        self._executor = action_executor
        self._scenes: Dict[str, List[Action]] = {}
        self._active_scene: Optional[str] = None

        logger.info("Scene Manager initialized")

    def create_scene(self, name: str, actions: List[Action]):
        """Create a scene."""
        self._scenes[name] = actions
        logger.info(f"Scene created: {name}")

    def remove_scene(self, name: str) -> bool:
        """Remove a scene."""
        if name in self._scenes:
            del self._scenes[name]
            if self._active_scene == name:
                self._active_scene = None
            logger.info(f"Scene removed: {name}")
            return True
        return False

    def activate_scene(self, name: str) -> bool:
        """Activate a scene."""
        if name not in self._scenes:
            logger.warning(f"Scene not found: {name}")
            return False

        logger.info(f"Activating scene: {name}")

        for action in self._scenes[name]:
            self._executor.execute(action)

        self._active_scene = name
        return True

    def get_active_scene(self) -> Optional[str]:
        """Get the currently active scene."""
        return self._active_scene

    def get_scene_names(self) -> List[str]:
        """Get all scene names."""
        return list(self._scenes.keys())

    def get_scene(self, name: str) -> Optional[List[Action]]:
        """Get scene actions."""
        return self._scenes.get(name)
