"""SQLite local persistent storage for TrailBuddy Local.

Provides zero-cloud, privacy-first local persistence for outdoor missions,
nature journal reflections, and mindful non-gamified progress tracking.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import config
from src.schemas import Mission, JournalEntry


class StorageManager:
    """Manages local SQLite database operations for missions and journal entries."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = str(db_path or config.DATABASE_PATH)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database schema if tables do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    tasks TEXT NOT NULL,
                    required_items TEXT NOT NULL,
                    safety_reminders TEXT NOT NULL,
                    reflection_question TEXT,
                    completed INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    user_reflection TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT,
                    mission_title TEXT NOT NULL,
                    date_completed TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    reflection TEXT,
                    completed INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.commit()

    def save_mission(self, mission: Mission) -> None:
        """Persist a new or updated Mission object."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO missions (
                    id, title, description, duration_minutes,
                    tasks, required_items, safety_reminders,
                    reflection_question, completed, completed_at,
                    user_reflection, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission.id,
                    mission.title,
                    mission.description,
                    mission.duration_minutes,
                    json.dumps(mission.tasks),
                    json.dumps(mission.required_items),
                    json.dumps(mission.safety_reminders),
                    mission.reflection_question,
                    1 if mission.completed else 0,
                    mission.completed_at,
                    mission.user_reflection,
                    mission.created_at,
                ),
            )
            conn.commit()

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Retrieve a specific mission by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_mission(row)

    def list_missions(self, limit: int = 50) -> List[Mission]:
        """List recently generated missions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM missions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            return [self._row_to_mission(r) for r in rows]

    def complete_mission(
        self,
        mission_id: str,
        reflection: Optional[str] = None,
        date_completed: Optional[str] = None,
    ) -> Optional[Mission]:
        """Mark a mission as complete and create a corresponding journal entry."""
        now_iso = date_completed or datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = cursor.fetchone()
            if not row:
                return None

            mission = self._row_to_mission(row)
            mission.completed = True
            mission.completed_at = now_iso
            mission.user_reflection = reflection

            # Update mission record
            cursor.execute(
                """
                UPDATE missions
                SET completed = 1, completed_at = ?, user_reflection = ?
                WHERE id = ?
                """,
                (now_iso, reflection, mission_id),
            )

            # Insert journal entry
            cursor.execute(
                """
                INSERT INTO journal_entries (
                    mission_id, mission_title, date_completed,
                    duration_minutes, reflection, completed
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    mission.id,
                    mission.title,
                    now_iso,
                    mission.duration_minutes,
                    reflection,
                ),
            )
            conn.commit()
            return mission

    def list_journal_entries(self, limit: int = 50) -> List[JournalEntry]:
        """Retrieve recorded nature journal entries ordered by date completed descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM journal_entries ORDER BY date_completed DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            entries = []
            for r in rows:
                entries.append(
                    JournalEntry(
                        id=r["id"],
                        mission_id=r["mission_id"],
                        mission_title=r["mission_title"],
                        date_completed=r["date_completed"],
                        duration_minutes=r["duration_minutes"],
                        reflection=r["reflection"],
                        completed=bool(r["completed"]),
                    )
                )
            return entries

    def get_progress_summary(self) -> Dict[str, Any]:
        """Compute a calm, non-gamified outdoor progress summary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as completed_count,
                    COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM missions
                WHERE completed = 1
            """)
            stats_row = cursor.fetchone()
            completed_count = stats_row["completed_count"] if stats_row else 0
            total_minutes = stats_row["total_minutes"] if stats_row else 0

            cursor.execute("""
                SELECT 
                    mission_title, date_completed, duration_minutes, reflection
                FROM journal_entries
                WHERE reflection IS NOT NULL AND TRIM(reflection) != ''
                ORDER BY date_completed DESC
                LIMIT 5
            """)
            reflection_rows = cursor.fetchall()
            recent_reflections = [
                {
                    "title": r["mission_title"],
                    "date": r["date_completed"],
                    "duration": r["duration_minutes"],
                    "reflection": r["reflection"],
                }
                for r in reflection_rows
            ]

            return {
                "completed_missions": completed_count,
                "total_outdoor_minutes": total_minutes,
                "recent_reflections": recent_reflections,
            }

    @staticmethod
    def _row_to_mission(row: sqlite3.Row) -> Mission:
        """Convert a database row into a validated Mission object."""
        return Mission(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            duration_minutes=row["duration_minutes"],
            tasks=json.loads(row["tasks"]),
            required_items=json.loads(row["required_items"]),
            safety_reminders=json.loads(row["safety_reminders"]),
            reflection_question=row["reflection_question"],
            completed=bool(row["completed"]),
            completed_at=row["completed_at"],
            user_reflection=row["user_reflection"],
            created_at=row["created_at"],
        )
