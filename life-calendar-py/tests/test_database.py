"""
Database, import/export and backup tests for Life Calendar 1.2.
Uses a temporary directory so the real user DB is never touched.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import date

# Point database module at a temp DB before importing it
TMP = Path(tempfile.mkdtemp(prefix="lc_test_"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import database as db

# Redirect DB path
db.DB_PATH = TMP / "test.db"


def setup_module():
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    db.init_db()


def teardown_module():
    shutil.rmtree(TMP, ignore_errors=True)


def test_init_and_schema_version():
    setup_module()
    assert db.get_setting("schema_version") == str(db.SCHEMA_VERSION)
    assert db.get_setting("first_day_of_week") == "0"
    cats = db.get_categories()
    assert len(cats) >= 8


def test_event_crud():
    setup_module()
    eid = db.add_event(
        title="Trip", note="Paris", category_id="travel",
        color="#06B6D4", week_year=25, week_number=10,
        start_date="2015-06-01", end_date="2015-06-07",
    )
    assert eid
    evs = db.get_events_for_week(25, 10)
    assert len(evs) == 1
    assert evs[0]["title"] == "Trip"

    db.update_event(eid, title="Trip to Lyon", note="Updated")
    evs = db.get_events_for_week(25, 10)
    assert evs[0]["title"] == "Trip to Lyon"
    assert evs[0]["note"] == "Updated"

    db.delete_event(eid)
    assert db.get_events_for_week(25, 10) == []


def test_week_colors():
    setup_module()
    db.add_event("A", "", "career", "#8B5CF6", 5, 3)
    colors = db.get_week_colors()
    assert (5, 3) in colors
    assert colors[(5, 3)] == "#8B5CF6"


def test_export_import_roundtrip():
    setup_module()
    db.add_event("Keep", "note", "other", "#6B7280", 1, 1)
    raw = db.export_data()
    data = json.loads(raw)
    assert "events" in data and len(data["events"]) == 1
    assert "settings" in data

    # Corrupt import must not destroy data
    try:
        db.import_data('{"events":[{"id":"x"}]}')  # missing required fields
        assert False, "should raise"
    except ValueError:
        pass
    # Original still there
    assert len(db.get_events_for_week(1, 1)) == 1

    # Valid re-import
    backup = db.import_data(raw)
    assert backup  # backup was created
    assert Path(backup).exists()
    assert len(db.get_events_for_week(1, 1)) == 1


def test_import_size_limit():
    setup_module()
    huge = '{"settings":{},"categories":[],"events":[]}' + (" " * (11 * 1024 * 1024))
    try:
        db.import_data(huge, max_bytes=10 * 1024 * 1024)
        assert False, "should raise on oversized payload"
    except ValueError as e:
        assert "большой" in str(e).lower() or "large" in str(e).lower() or "МБ" in str(e)


def test_backup_and_restore():
    setup_module()
    db.add_event("Important", "do not lose", "achievements", "#10B981", 12, 0)
    backup = db.backup_database()
    assert backup and Path(backup).exists()

    # Destroy data
    for ev in db.get_all_events():
        db.delete_event(ev["id"])
    assert db.get_events_for_week(12, 0) == []

    # Restore
    db.restore_from_backup(Path(backup))
    restored = db.get_events_for_week(12, 0)
    assert len(restored) == 1
    assert restored[0]["title"] == "Important"


def test_foreign_keys_pragma():
    setup_module()
    conn = db.get_connection()
    try:
        row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1
    finally:
        conn.close()




def test_backup_raises_on_api_failure(monkeypatch=None):
    """If Online Backup API fails, RuntimeError is raised (no shutil fallback)."""
    setup_module()
    db.add_event("X", "", "other", "#6B7280", 0, 0)

    real_connect = db.sqlite3.connect

    def boom(*args, **kwargs):
        # Allow opening source; fail when creating destination-like path
        path = args[0] if args else kwargs.get("database", "")
        if "backup" in str(path):
            raise sqlite3.OperationalError("simulated backup failure")
        return real_connect(*args, **kwargs)

    import sqlite3
    original = db.sqlite3.connect
    db.sqlite3.connect = boom
    try:
        raised = False
        try:
            db.backup_database()
        except RuntimeError as e:
            raised = True
            assert "резервн" in str(e).lower() or "backup" in str(e).lower() or "Не удалось" in str(e)
        assert raised, "backup_database must raise RuntimeError on API failure"
    finally:
        db.sqlite3.connect = original


def test_import_aborts_if_backup_fails():
    """Import must not mutate data when backup cannot be created."""
    setup_module()
    eid = db.add_event("KeepMe", "important", "other", "#6B7280", 3, 3)
    raw_before = db.export_data()

    import sqlite3
    original = db.sqlite3.connect
    real_connect = original

    def boom(*args, **kwargs):
        path = args[0] if args else ""
        if "backup" in str(path):
            raise sqlite3.OperationalError("simulated backup failure")
        return real_connect(*args, **kwargs)

    db.sqlite3.connect = boom
    try:
        raised = False
        try:
            db.import_data(raw_before)
        except RuntimeError:
            raised = True
        assert raised
    finally:
        db.sqlite3.connect = original

    # Data unchanged
    evs = db.get_events_for_week(3, 3)
    assert len(evs) == 1 and evs[0]["title"] == "KeepMe"


def test_cache_invalidation_after_crud():
    """Mirrors main.py cache rules: clear after mutation, then refill."""
    setup_module()
    cache = {}

    def get_cached(y, w):
        key = (y, w)
        if key not in cache:
            cache[key] = db.get_events_for_week(y, w)
        return cache[key]

    eid = db.add_event("C1", "", "other", "#6B7280", 7, 7)
    cache.clear()
    assert len(get_cached(7, 7)) == 1

    db.update_event(eid, title="C2")
    cache.clear()  # same as refresh_data / pop after mutation
    assert get_cached(7, 7)[0]["title"] == "C2"

    db.delete_event(eid)
    cache.clear()
    assert get_cached(7, 7) == []

if __name__ == "__main__":
    tests = [
        test_init_and_schema_version,
        test_event_crud,
        test_week_colors,
        test_export_import_roundtrip,
        test_import_size_limit,
        test_backup_and_restore,
        test_foreign_keys_pragma,
        test_backup_raises_on_api_failure,
        test_import_aborts_if_backup_fails,
        test_cache_invalidation_after_crud,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    teardown_module()
    sys.exit(1 if failed else 0)
