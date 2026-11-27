"""
Ensure user DB and Python cache artefacts are not tracked / not present in the package tree.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_gitignore_exists_and_covers_critical_patterns():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required = [
        "__pycache__/",
        "*.py[cod]",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*.db-wal",
        "*.db-shm",
        ".venv/",
        ".pytest_cache/",
    ]
    for pat in required:
        assert pat in gi, f".gitignore missing pattern: {pat}"


def test_no_db_or_pycache_in_tree():
    """Working tree must not ship user databases or bytecode."""
    bad = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            # allow empty __pycache__ dirs? better none
            if p.name == "__pycache__":
                bad.append(str(p.relative_to(ROOT)))
            continue
        rel = str(p.relative_to(ROOT))
        if p.suffix in {".db", ".sqlite", ".sqlite3", ".pyc"}:
            # allow nothing
            bad.append(rel)
        if p.name.endswith(("-wal", "-shm")) and "life_calendar" in p.name:
            bad.append(rel)
        if "life_calendar_backup_" in p.name:
            bad.append(rel)
    assert bad == [], f"Forbidden artefacts present: {bad}"


def test_data_gitkeep_only():
    data = ROOT / "data"
    assert data.is_dir()
    names = sorted(p.name for p in data.iterdir())
    assert names == [".gitkeep"], f"data/ should only contain .gitkeep, got {names}"


if __name__ == "__main__":
    failed = 0
    for t in (
        test_gitignore_exists_and_covers_critical_patterns,
        test_no_db_or_pycache_in_tree,
        test_data_gitkeep_only,
    ):
        try:
            t()
            print(f"  OK  {t.__name__}")
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{3 - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
