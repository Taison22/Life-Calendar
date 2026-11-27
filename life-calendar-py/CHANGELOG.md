# Changelog

## [1.2.1] — 2026-11-27 — Hotfix

### Security / data safety
- `backup_database()` no longer falls back to `shutil.copy2` on WAL databases
- On Online Backup API failure raises `RuntimeError` with a clear message
- `import_data()` aborts if an existing DB cannot be backed up successfully

### Cache
- `refresh_list()` in the week dialog: single invalidate + fetch (removed redundant double query)

### Tests
- `tests/test_repo_hygiene.py` — .gitignore patterns, no DB/pyc in tree
- Extended `test_database.py`: backup failure, import abort, cache after CRUD

---

## [1.2] — 2026-11-27 — Technical Hardening

### Reliability & Data Safety
- SQLite Online Backup API (`Connection.backup`) instead of raw file copy
- `restore_from_backup()` for verified recovery
- Schema versioning (`schema_version` in settings) with sequential migrations
- Index on `events(category_id)` added (idempotent migration)
- Import size limit (10 MB) to reject oversized payloads
- Context-manager helper `db_connection()` documented; every connection enables `foreign_keys=ON` and WAL

### Performance
- Single reusable tooltip `Toplevel` (no create/destroy on every mouse move)
- Event cache invalidated on create / edit / delete / import
- Tooltip cleaned up on application close

### Calendar clarity
- Documented that life-grid weeks are birthday-based
- `first_day_of_week` only affects auxiliary helpers, not the 52-week life grid

### Testing
- `tests/test_calculations.py` — 7 tests (leap years, boundaries, week helpers)
- `tests/test_database.py` — 7 tests (CRUD, import validation, backup/restore, PRAGMA)
- `tests/test_cache_logic.py` — cache invalidation logic

### Repository hygiene
- `.gitignore` excludes `__pycache__`, `*.db`, WAL/SHM, backups, venv, IDE files
- User data never committed

### Compatibility
- Existing 1.1 databases open without data loss
- Migration only writes `schema_version` and ensures indexes

---

## [1.1] — 2026-11-27

- Event editing (title, note, category, color)
- Navigation from events list highlights target week
- Event cache for tooltips
- Safer JSON import with validation + pre-import backup
- Default `first_day_of_week` = Monday (0)
- Initial calculation tests

---

## [1.0] — 2026-11-27

- Initial release: life grid, stats, events, settings, local SQLite
