"""
IoT Device Mesh Integration System - Database Integration Module
=============================================================
SQLite database integration for device management, rules storage,
and historical data persistence.

Author: NeuralBlitz Systems
Version: 2.0.0
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeviceRecord:
    """Device database record."""

    device_id: str
    name: str
    device_type: str
    ip_address: str
    mac_address: str
    port: int
    protocol: str
    state: str
    properties_json: str
    capabilities_json: str
    firmware_version: str
    manufacturer: str
    last_seen: str
    created_at: str
    updated_at: str


@dataclass
class AutomationRuleRecord:
    """Automation rule database record."""

    rule_id: str
    name: str
    description: str
    enabled: int
    triggers_json: str
    conditions_json: str
    actions_json: str
    priority: int
    max_executions: int
    cooldown_seconds: float
    tags_json: str
    created_at: str
    updated_at: str


class DatabaseManager:
    """SQLite database manager for IoT mesh system."""

    def __init__(self, db_path: str = "iot_mesh.db"):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

        self._init_database()
        logger.info(f"Database initialized: {db_path}")

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    ip_address TEXT,
                    mac_address TEXT,
                    port INTEGER,
                    protocol TEXT,
                    state TEXT DEFAULT 'offline',
                    properties_json TEXT DEFAULT '{}',
                    capabilities_json TEXT DEFAULT '{}',
                    firmware_version TEXT DEFAULT 'unknown',
                    manufacturer TEXT DEFAULT 'unknown',
                    last_seen TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Automation rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    triggers_json TEXT DEFAULT '[]',
                    conditions_json TEXT DEFAULT '[]',
                    actions_json TEXT DEFAULT '[]',
                    priority INTEGER DEFAULT 0,
                    max_executions INTEGER DEFAULT 0,
                    cooldown_seconds REAL DEFAULT 0,
                    tags_json TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Device state history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES devices(device_id)
                )
            """)

            # Execution history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    context_json TEXT DEFAULT '{}',
                    executed_at TEXT NOT NULL,
                    FOREIGN KEY (rule_id) REFERENCES automation_rules(rule_id)
                )
            """)

            # Scenes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    scene_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_state_history_device_id 
                ON device_state_history(device_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_state_history_timestamp 
                ON device_state_history(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_history_rule_id 
                ON execution_history(rule_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_history_executed_at 
                ON execution_history(executed_at)
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # =========================================================================
    # DEVICE OPERATIONS
    # =========================================================================

    def insert_device(self, device: DeviceRecord) -> bool:
        """Insert a new device."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO devices (
                            device_id, name, device_type, ip_address, mac_address,
                            port, protocol, state, properties_json, capabilities_json,
                            firmware_version, manufacturer, last_seen, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            device.device_id,
                            device.name,
                            device.device_type,
                            device.ip_address,
                            device.mac_address,
                            device.port,
                            device.protocol,
                            device.state,
                            device.properties_json,
                            device.capabilities_json,
                            device.firmware_version,
                            device.manufacturer,
                            device.last_seen,
                            device.created_at,
                            device.updated_at,
                        ),
                    )
                    conn.commit()
                    return True
            except sqlite3.IntegrityError:
                logger.warning(f"Device already exists: {device.device_id}")
                return False

    def update_device(self, device: DeviceRecord) -> bool:
        """Update an existing device."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE devices SET
                            name = ?, device_type = ?, ip_address = ?, mac_address = ?,
                            port = ?, protocol = ?, state = ?, properties_json = ?,
                            capabilities_json = ?, firmware_version = ?, manufacturer = ?,
                            last_seen = ?, updated_at = ?
                        WHERE device_id = ?
                    """,
                        (
                            device.name,
                            device.device_type,
                            device.ip_address,
                            device.mac_address,
                            device.port,
                            device.protocol,
                            device.state,
                            device.properties_json,
                            device.capabilities_json,
                            device.firmware_version,
                            device.manufacturer,
                            device.last_seen,
                            device.updated_at,
                            device.device_id,
                        ),
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to update device: {e}")
                return False

    def delete_device(self, device_id: str) -> bool:
        """Delete a device."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM devices WHERE device_id = ?", (device_id,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to delete device: {e}")
                return False

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get a device by ID."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM devices WHERE device_id = ?", (device_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM devices ORDER BY name")
                return [dict(row) for row in cursor.fetchall()]

    def get_devices_by_type(self, device_type: str) -> List[Dict[str, Any]]:
        """Get devices by type."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM devices WHERE device_type = ? ORDER BY name",
                    (device_type,),
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_devices_by_state(self, state: str) -> List[Dict[str, Any]]:
        """Get devices by state."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM devices WHERE state = ? ORDER BY name", (state,)
                )
                return [dict(row) for row in cursor.fetchall()]

    def save_device_state_history(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Save device state to history."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO device_state_history (device_id, state_json, timestamp)
                        VALUES (?, ?, ?)
                    """,
                        (device_id, json.dumps(state), datetime.now().isoformat()),
                    )
                    conn.commit()

                    # Cleanup old records (keep last 1000 per device)
                    cursor.execute(
                        """
                        DELETE FROM device_state_history
                        WHERE device_id = ? AND id NOT IN (
                            SELECT id FROM device_state_history
                            WHERE device_id = ?
                            ORDER BY timestamp DESC
                            LIMIT 1000
                        )
                    """,
                        (device_id, device_id),
                    )
                    conn.commit()

                    return True
            except Exception as e:
                logger.error(f"Failed to save device state history: {e}")
                return False

    def get_device_state_history(
        self, device_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get device state history."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM device_state_history
                    WHERE device_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (device_id, limit),
                )
                return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # AUTOMATION RULE OPERATIONS
    # =========================================================================

    def insert_automation_rule(self, rule: AutomationRuleRecord) -> bool:
        """Insert a new automation rule."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO automation_rules (
                            rule_id, name, description, enabled, triggers_json,
                            conditions_json, actions_json, priority, max_executions,
                            cooldown_seconds, tags_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            rule.rule_id,
                            rule.name,
                            rule.description,
                            rule.enabled,
                            rule.triggers_json,
                            rule.conditions_json,
                            rule.actions_json,
                            rule.priority,
                            rule.max_executions,
                            rule.cooldown_seconds,
                            rule.tags_json,
                            rule.created_at,
                            rule.updated_at,
                        ),
                    )
                    conn.commit()
                    return True
            except sqlite3.IntegrityError:
                logger.warning(f"Rule already exists: {rule.rule_id}")
                return False

    def update_automation_rule(self, rule: AutomationRuleRecord) -> bool:
        """Update an automation rule."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE automation_rules SET
                            name = ?, description = ?, enabled = ?, triggers_json = ?,
                            conditions_json = ?, actions_json = ?, priority = ?,
                            max_executions = ?, cooldown_seconds = ?, tags_json = ?,
                            updated_at = ?
                        WHERE rule_id = ?
                    """,
                        (
                            rule.name,
                            rule.description,
                            rule.enabled,
                            rule.triggers_json,
                            rule.conditions_json,
                            rule.actions_json,
                            rule.priority,
                            rule.max_executions,
                            rule.cooldown_seconds,
                            rule.tags_json,
                            rule.updated_at,
                            rule.rule_id,
                        ),
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to update rule: {e}")
                return False

    def delete_automation_rule(self, rule_id: str) -> bool:
        """Delete an automation rule."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM automation_rules WHERE rule_id = ?", (rule_id,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to delete rule: {e}")
                return False

    def get_automation_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get an automation rule by ID."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM automation_rules WHERE rule_id = ?", (rule_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_automation_rules(self) -> List[Dict[str, Any]]:
        """Get all automation rules."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM automation_rules ORDER BY priority DESC, name"
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_enabled_automation_rules(self) -> List[Dict[str, Any]]:
        """Get enabled automation rules."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM automation_rules 
                    WHERE enabled = 1 
                    ORDER BY priority DESC, name
                """)
                return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # EXECUTION HISTORY OPERATIONS
    # =========================================================================

    def save_execution_history(
        self, rule_id: str, rule_name: str, context: Dict[str, Any]
    ) -> bool:
        """Save execution history."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO execution_history (rule_id, rule_name, context_json, executed_at)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            rule_id,
                            rule_name,
                            json.dumps(context),
                            datetime.now().isoformat(),
                        ),
                    )
                    conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to save execution history: {e}")
                return False

    def get_execution_history(
        self, rule_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get execution history."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if rule_id:
                    cursor.execute(
                        """
                        SELECT * FROM execution_history
                        WHERE rule_id = ?
                        ORDER BY executed_at DESC
                        LIMIT ?
                    """,
                        (rule_id, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM execution_history
                        ORDER BY executed_at DESC
                        LIMIT ?
                    """,
                        (limit,),
                    )
                return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # SCENE OPERATIONS
    # =========================================================================

    def save_scene(
        self, scene_id: str, name: str, actions: List[Dict[str, Any]]
    ) -> bool:
        """Save a scene."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO scenes (scene_id, name, actions_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (scene_id, name, json.dumps(actions), now, now),
                    )
                    conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Failed to save scene: {e}")
                return False

    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM scenes WHERE scene_id = ?", (scene_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_scenes(self) -> List[Dict[str, Any]]:
        """Get all scenes."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM scenes ORDER BY name")
                return [dict(row) for row in cursor.fetchall()]

    def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM scenes WHERE scene_id = ?", (scene_id,))
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Failed to delete scene: {e}")
                return False

    # =========================================================================
    # STATISTICS AND AGGREGATIONS
    # =========================================================================

    def get_device_count(self) -> int:
        """Get total device count."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM devices")
                return cursor.fetchone()[0]

    def get_rule_count(self) -> int:
        """Get total rule count."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM automation_rules")
                return cursor.fetchone()[0]

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {"devices": {}, "rules": {}, "history": {}}

                # Device stats by type
                cursor.execute("""
                    SELECT device_type, COUNT(*) as count 
                    FROM devices GROUP BY device_type
                """)
                stats["devices"]["by_type"] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }

                # Device stats by state
                cursor.execute("""
                    SELECT state, COUNT(*) as count 
                    FROM devices GROUP BY state
                """)
                stats["devices"]["by_state"] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }

                # Rule stats
                cursor.execute("SELECT COUNT(*) FROM automation_rules")
                stats["rules"]["total"] = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM automation_rules WHERE enabled = 1"
                )
                stats["rules"]["enabled"] = cursor.fetchone()[0]

                # History stats
                cursor.execute("SELECT COUNT(*) FROM device_state_history")
                stats["history"]["device_states"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM execution_history")
                stats["history"]["executions"] = cursor.fetchone()[0]

                return stats

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
