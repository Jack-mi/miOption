from pathlib import Path

from signal_chain.data import archive


def test_archive_preserves_versions_and_only_indexes_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("MIOPTION_ARCHIVE_DIR", raising=False)
    source = tmp_path / "reports" / "US.TEST.md"
    source.parent.mkdir()
    source.write_text("old report with account and price")
    old = archive.preserve(source)
    assert old is not None and old.read_text() == source.read_text()
    assert old.stat().st_mode & 0o777 == 0o600
    source.write_text("new report with account and price")
    new = archive.preserve(source)
    assert new is not None and new != old and old.read_text() != new.read_text()
    rows = [archive.entry(path) for path in archive.inventory()]
    assert len(rows) == 3
    assert archive.preserve(old) == old
    assert len(archive.inventory()) == 3
    assert {row["ticker"] for row in rows} == {"US.TEST"}
    assert all(row["quality"] == "legacy_unverified" and row["payload"]["local_only"] for row in rows)
    assert all("account and price" not in str(row) for row in rows)
