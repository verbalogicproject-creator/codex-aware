from __future__ import annotations

from codex_aware.scanner import scan_project


def test_scanner_excludes_secrets_and_source_bodies(tmp_path):
    (tmp_path / ".env.local").write_text("OPENAI_API_KEY=secret")
    source = tmp_path / "src"
    source.mkdir()
    (source / "commands.ts").write_text('export const x = { name: "delete_task", secret: "not exported as content" }')
    snapshot = scan_project(tmp_path, "sample")
    serialized = str(snapshot)
    assert "OPENAI_API_KEY" not in serialized
    assert "secret" not in serialized
    assert snapshot["commands"][0]["name"] == "delete_task"
    assert snapshot["files"][0]["uri"].startswith("repo://sample/")

