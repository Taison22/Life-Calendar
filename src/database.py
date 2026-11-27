"""
Life Calendar - Database module
SQLite storage for settings, categories, and events.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import shutil

DB_PATH = Path(__file__).parent.parent / "data" / "life_calendar.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL,
            is_system INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            note TEXT,
            category_id TEXT,
            color TEXT,
            week_year INTEGER NOT NULL,
            week_number INTEGER NOT NULL,
            start_date TEXT,
            end_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_week 
        ON events(week_year, week_number)
    """)

    # Default categories
    defaults = [
        ("education", "Образование", "#3B82F6"),
        ("career", "Работа и карьера", "#8B5CF6"),
        ("travel", "Путешествия", "#06B6D4"),
        ("family", "Семья и друзья", "#F59E0B"),
        ("achievements", "Личные достижения", "#10B981"),
        ("projects", "Проекты", "#EF4444"),
        ("rest", "Отдых", "#84CC16"),
        ("other", "Другое", "#6B7280"),
    ]

    now = datetime.utcnow().isoformat()
    for cid, name, color in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO categories (id, name, color, is_system, created_at) VALUES (?, ?, ?, 1, ?)",
            (cid, name, color, now)
        )

    # Default settings
    # first_day_of_week: 0 = Monday, 6 = Sunday (Python weekday style)
    defaults_settings = {
        "birth_date": "",
        "life_expectancy": "90",
        "first_day_of_week": "0",  # Monday by default
        "theme": "dark",
        "setup_completed": "0",
    }
    for k, v in defaults_settings.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (k, v)
        )

    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_categories() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY is_system DESC, name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name: str, color: str) -> str:
    cid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO categories (id, name, color, is_system, created_at) VALUES (?, ?, ?, 0, ?)",
        (cid, name, color, now)
    )
    conn.commit()
    conn.close()
    return cid


def get_events_for_week(year: int, week: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.*, c.name as category_name, c.color as category_color
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.week_year = ? AND e.week_number = ?
        ORDER BY e.created_at
        """,
        (year, week)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_events(search: str = "", category_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT e.*, c.name as category_name, c.color as category_color
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE 1=1
    """
    params: List[Any] = []
    if search:
        query += " AND (e.title LIKE ? OR e.note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id:
        query += " AND e.category_id = ?"
        params.append(category_id)
    query += " ORDER BY e.week_year, e.week_number, e.created_at"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_event(
    title: str,
    note: str,
    category_id: Optional[str],
    color: Optional[str],
    week_year: int,
    week_number: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    eid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (id, title, note, category_id, color, week_year, week_number, start_date, end_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (eid, title, note, category_id, color, week_year, week_number, start_date, end_date, now, now)
    )
    conn.commit()
    conn.close()
    return eid


def update_event(event_id: str, **kwargs) -> None:
    allowed = {"title", "note", "category_id", "color", "start_date", "end_date"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [event_id]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE events SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_event(event_id: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


def get_week_colors() -> Dict[tuple, str]:
    """Return map of (year, week) -> dominant color for events."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT week_year, week_number, 
               COALESCE(color, (SELECT color FROM categories WHERE id = category_id), '#3B82F6') as col
        FROM events
        ORDER BY created_at DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    result: Dict[tuple, str] = {}
    for r in rows:
        key = (r["week_year"], r["week_number"])
        if key not in result:
            result[key] = r["col"]
    return result


def export_data() -> str:
    """Export all data as JSON string."""
    data = {
        "settings": get_all_settings(),
        "categories": get_categories(),
        "events": get_all_events(),
        "exported_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _validate_import_data(data: Any) -> None:
    """Raise ValueError if structure is invalid."""
    if not isinstance(data, dict):
        raise ValueError("Корневой объект JSON должен быть объектом")
    if "settings" in data and not isinstance(data["settings"], dict):
        raise ValueError("Поле settings должно быть объектом")
    if "categories" in data and not isinstance(data["categories"], list):
        raise ValueError("Поле categories должно быть массивом")
    if "events" in data and not isinstance(data["events"], list):
        raise ValueError("Поле events должно быть массивом")

    for i, cat in enumerate(data.get("categories") or []):
        if not isinstance(cat, dict):
            raise ValueError(f"categories[{i}] должен быть объектом")
        for field in ("id", "name", "color"):
            if field not in cat:
                raise ValueError(f"categories[{i}] не содержит обязательное поле '{field}'")

    for i, ev in enumerate(data.get("events") or []):
        if not isinstance(ev, dict):
            raise ValueError(f"events[{i}] должен быть объектом")
        for field in ("id", "title", "week_year", "week_number"):
            if field not in ev:
                raise ValueError(f"events[{i}] не содержит обязательное поле '{field}'")
        if not isinstance(ev["week_year"], int) or not isinstance(ev["week_number"], int):
            raise ValueError(f"events[{i}]: week_year и week_number должны быть целыми числами")


def backup_database() -> Optional[Path]:
    """Create a timestamped backup of the current DB. Returns path or None."""
    if not DB_PATH.exists():
        return None
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.parent / f"life_calendar_backup_{ts}.db"
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def import_data(json_str: str) -> str:
    """
    Safely import data from JSON string.
    - Validates structure
    - Creates automatic backup before changes
    - Uses a transaction; rolls back on any error
    Returns path of the backup file (or empty string).
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Некорректный JSON: {e}") from e

    _validate_import_data(data)

    backup_path = backup_database()
    backup_str = str(backup_path) if backup_path else ""

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")

        # Clear user data (keep system categories)
        cur.execute("DELETE FROM events")
        cur.execute("DELETE FROM categories WHERE is_system = 0")

        # Settings
        for k, v in (data.get("settings") or {}).items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (k, v)
            )

        # Custom categories
        for cat in data.get("categories") or []:
            if cat.get("is_system"):
                continue
            cur.execute(
                "INSERT OR REPLACE INTO categories (id, name, color, is_system, created_at) "
                "VALUES (?, ?, ?, 0, ?)",
                (
                    cat["id"],
                    cat["name"],
                    cat["color"],
                    cat.get("created_at", datetime.utcnow().isoformat()),
                )
            )

        # Events
        for ev in data.get("events") or []:
            cur.execute(
                """
                INSERT OR REPLACE INTO events
                (id, title, note, category_id, color, week_year, week_number,
                 start_date, end_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev["id"],
                    ev["title"],
                    ev.get("note"),
                    ev.get("category_id"),
                    ev.get("color"),
                    ev["week_year"],
                    ev["week_number"],
                    ev.get("start_date"),
                    ev.get("end_date"),
                    ev.get("created_at", datetime.utcnow().isoformat()),
                    ev.get("updated_at", datetime.utcnow().isoformat()),
                )
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return backup_str
