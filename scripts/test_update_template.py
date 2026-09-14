#!/usr/bin/env python3
"""Integration tests for update_template.py using temporary Git repositories."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


UPDATER = Path(__file__).with_name("update_template.py").resolve()
MARKER = "## User-Specific Rules"


def run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


class TemporaryFork:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agentic-updater-test-")
        self.root = Path(self.temporary.name)
        self.upstream = self.root / "upstream"
        self.local = self.root / "local"

        self.upstream.mkdir()
        run(["git", "init", "-q", "-b", "main"], self.upstream)
        run(["git", "config", "user.email", "test@example.com"], self.upstream)
        run(["git", "config", "user.name", "Updater Test"], self.upstream)

        self.write_upstream("README.md", "baseline readme\n")
        self.write_upstream(
            "AGENTS.md",
            f"# Baseline rules\n\n{MARKER}\n\nupstream placeholder\n",
        )
        self.write_upstream("templates/remove.txt", "keep unless reviewed\n")
        manifest = {
            "schema_version": 1,
            "files": [
                {"path": "README.md", "type": "file"},
                {"path": "AGENTS.md", "type": "instruction"},
                {"path": "scripts/template_manifest.json", "type": "file"},
                {"path": "templates/new.txt", "type": "placeholder"},
                {"path": "templates/remove.txt", "type": "placeholder"},
            ],
        }
        self.write_upstream(
            "scripts/template_manifest.json",
            json.dumps(manifest, indent=2) + "\n",
        )
        self.commit_upstream("baseline")

        run(["git", "clone", "-q", str(self.upstream), str(self.local)], self.root)
        run(["git", "remote", "rename", "origin", "upstream"], self.local)
        run(["git", "config", "user.email", "test@example.com"], self.local)
        run(["git", "config", "user.name", "Updater Test"], self.local)

    def close(self) -> None:
        self.temporary.cleanup()

    def write_upstream(self, relative: str, content: str | bytes) -> None:
        path = self.upstream / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")

    def write_local(self, relative: str, content: str | bytes) -> None:
        path = self.local / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")

    def commit_upstream(self, message: str) -> str:
        run(["git", "add", "-A"], self.upstream)
        run(["git", "commit", "-q", "-m", message], self.upstream)
        return run(["git", "rev-parse", "HEAD"], self.upstream).stdout.strip()

    def updater(self, command: str) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(UPDATER), command], self.local, check=False)

    def local_bytes(self, relative: str) -> bytes:
        return (self.local / relative).read_bytes()


class UpdateTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fork = TemporaryFork()

    def tearDown(self) -> None:
        self.fork.close()

    def output(self, result: subprocess.CompletedProcess[str]) -> str:
        return result.stdout + result.stderr

    def test_no_upstream_update_check_is_read_only(self) -> None:
        before = self.fork.local_bytes("README.md")
        result = self.fork.updater("check")
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("[unchanged] README.md", result.stdout)
        self.assertEqual(self.fork.local_bytes("README.md"), before)
        self.assertFalse((self.fork.local / ".agentic-sandbox-state.json").exists())

    def test_safe_update_of_unmodified_public_file(self) -> None:
        self.fork.write_upstream("README.md", "upstream readme v2\n")
        latest = self.fork.commit_upstream("update readme")

        checked = self.fork.updater("check")
        self.assertEqual(checked.returncode, 0, self.output(checked))
        self.assertIn("[safe update] README.md", checked.stdout)
        self.assertEqual(self.fork.local_bytes("README.md"), b"baseline readme\n")

        applied = self.fork.updater("apply")
        self.assertEqual(applied.returncode, 0, self.output(applied))
        self.assertEqual(self.fork.local_bytes("README.md"), b"upstream readme v2\n")
        state = json.loads(
            (self.fork.local / ".agentic-sandbox-state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["upstream_commit"], latest)

    def test_conflict_aborts_every_write(self) -> None:
        self.fork.write_local("README.md", "local readme edit\n")
        before_agents = self.fork.local_bytes("AGENTS.md")
        self.fork.write_upstream("README.md", "upstream readme edit\n")
        self.fork.write_upstream(
            "AGENTS.md",
            f"# Upstream rules v2\n\n{MARKER}\n\nupstream placeholder\n",
        )
        self.fork.commit_upstream("two upstream changes")

        result = self.fork.updater("apply")
        self.assertEqual(result.returncode, 2, self.output(result))
        self.assertIn("[conflict] README.md", result.stdout)
        self.assertIn("No working-tree files", result.stdout)
        self.assertEqual(self.fork.local_bytes("README.md"), b"local readme edit\n")
        self.assertEqual(self.fork.local_bytes("AGENTS.md"), before_agents)
        self.assertFalse((self.fork.local / ".agentic-sandbox-state.json").exists())

    def test_instruction_user_section_is_byte_preserved(self) -> None:
        suffix = (f"{MARKER}\r\n\r\n- 用户规则  그대로\r\n").encode("utf-8")
        self.fork.write_local("AGENTS.md", b"# Baseline rules\n\n" + suffix)
        self.fork.write_upstream(
            "AGENTS.md",
            f"# Upstream rules v2\n\n{MARKER}\n\nupstream placeholder\n",
        )
        self.fork.commit_upstream("update public rules")

        result = self.fork.updater("apply")
        self.assertEqual(result.returncode, 0, self.output(result))
        updated = self.fork.local_bytes("AGENTS.md")
        marker_offset = updated.index(MARKER.encode("utf-8"))
        self.assertEqual(updated[marker_offset:], suffix)
        self.assertTrue(updated.startswith(b"# Upstream rules v2\n"))

    def test_unlisted_projects_data_and_archive_are_untouched(self) -> None:
        protected = {
            "projects/actual-study/results.csv": b"project results\n",
            "panel_factory/data/raw/private.csv": b"private data\n",
            "archive/legacy/source.R": b"legacy source\n",
            "notes/unlisted.txt": b"user note\n",
        }
        for relative, content in protected.items():
            self.fork.write_local(relative, content)
        self.fork.write_upstream("README.md", "safe public update\n")
        self.fork.commit_upstream("update public file")

        result = self.fork.updater("apply")
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("all paths outside the local manifest", result.stdout)
        for relative, content in protected.items():
            self.assertEqual(self.fork.local_bytes(relative), content)

    def test_upstream_placeholder_addition(self) -> None:
        self.fork.write_upstream("templates/new.txt", "new placeholder\n")
        self.fork.commit_upstream("add placeholder")

        checked = self.fork.updater("check")
        self.assertEqual(checked.returncode, 0, self.output(checked))
        self.assertIn("[add] templates/new.txt", checked.stdout)
        self.assertFalse((self.fork.local / "templates/new.txt").exists())

        applied = self.fork.updater("apply")
        self.assertEqual(applied.returncode, 0, self.output(applied))
        self.assertEqual(self.fork.local_bytes("templates/new.txt"), b"new placeholder\n")

    def test_new_manifest_path_is_added_on_followup_run(self) -> None:
        manifest_path = self.fork.upstream / "scripts/template_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append(
            {"path": "templates/future.txt", "type": "placeholder"}
        )
        self.fork.write_upstream(
            "scripts/template_manifest.json", json.dumps(manifest, indent=2) + "\n"
        )
        self.fork.write_upstream("templates/future.txt", "future placeholder\n")
        self.fork.commit_upstream("expand manifest and add placeholder")

        first = self.fork.updater("apply")
        self.assertEqual(first.returncode, 0, self.output(first))
        self.assertFalse((self.fork.local / "templates/future.txt").exists())

        second = self.fork.updater("apply")
        self.assertEqual(second.returncode, 0, self.output(second))
        self.assertIn("[add] templates/future.txt", second.stdout)
        self.assertEqual(
            self.fork.local_bytes("templates/future.txt"), b"future placeholder\n"
        )

    def test_upstream_deletion_requires_review_and_does_not_delete(self) -> None:
        run(["git", "rm", "-q", "templates/remove.txt"], self.fork.upstream)
        self.fork.commit_upstream("remove placeholder upstream")

        result = self.fork.updater("apply")
        self.assertEqual(result.returncode, 0, self.output(result))
        self.assertIn("[manual review] templates/remove.txt", result.stdout)
        self.assertEqual(
            self.fork.local_bytes("templates/remove.txt"), b"keep unless reviewed\n"
        )

    def test_repeated_apply_is_idempotent(self) -> None:
        self.fork.write_upstream("README.md", "idempotent update\n")
        self.fork.commit_upstream("idempotent update")

        first = self.fork.updater("apply")
        self.assertEqual(first.returncode, 0, self.output(first))
        before = {
            "README.md": self.fork.local_bytes("README.md"),
            "AGENTS.md": self.fork.local_bytes("AGENTS.md"),
            "state": self.fork.local_bytes(".agentic-sandbox-state.json"),
        }
        status_before = run(["git", "status", "--short"], self.fork.local).stdout

        second = self.fork.updater("apply")
        self.assertEqual(second.returncode, 0, self.output(second))
        self.assertIn("Applied 0 managed file update(s)", second.stdout)
        self.assertEqual(self.fork.local_bytes("README.md"), before["README.md"])
        self.assertEqual(self.fork.local_bytes("AGENTS.md"), before["AGENTS.md"])
        self.assertEqual(
            self.fork.local_bytes(".agentic-sandbox-state.json"), before["state"]
        )
        self.assertEqual(run(["git", "status", "--short"], self.fork.local).stdout, status_before)

    def test_invalid_marker_aborts_without_writes(self) -> None:
        self.fork.write_local("AGENTS.md", "# Marker removed locally\n")
        self.fork.write_upstream("README.md", "otherwise safe update\n")
        self.fork.commit_upstream("safe update beside bad marker")
        before_readme = self.fork.local_bytes("README.md")

        result = self.fork.updater("apply")
        self.assertEqual(result.returncode, 2, self.output(result))
        self.assertIn("expected exactly 1", result.stdout)
        self.assertEqual(self.fork.local_bytes("README.md"), before_readme)
        self.assertFalse((self.fork.local / ".agentic-sandbox-state.json").exists())

    def test_managed_symlink_is_a_conflict_and_apply_is_zero_write(self) -> None:
        external = self.fork.root / "external-readme.txt"
        external.write_bytes(b"outside target\n")
        readme = self.fork.local / "README.md"
        readme.unlink()
        readme.symlink_to(external)
        self.fork.write_upstream(
            "AGENTS.md",
            f"# Upstream rules v2\n\n{MARKER}\n\nupstream placeholder\n",
        )
        self.fork.commit_upstream("update beside managed symlink")
        before_agents = self.fork.local_bytes("AGENTS.md")

        result = self.fork.updater("apply")

        self.assertEqual(result.returncode, 2, self.output(result))
        self.assertIn("[conflict] README.md", result.stdout)
        self.assertIn("symlink synchronization is unsupported", result.stdout)
        self.assertTrue(readme.is_symlink())
        self.assertEqual(external.read_bytes(), b"outside target\n")
        self.assertEqual(self.fork.local_bytes("AGENTS.md"), before_agents)
        self.assertFalse((self.fork.local / ".agentic-sandbox-state.json").exists())

    def test_symlinked_parent_of_managed_path_is_a_conflict(self) -> None:
        external = self.fork.root / "external-templates"
        external.mkdir()
        (external / "remove.txt").write_bytes(b"outside target\n")
        templates = self.fork.local / "templates"
        (templates / "remove.txt").unlink()
        templates.rmdir()
        templates.symlink_to(external, target_is_directory=True)

        result = self.fork.updater("check")

        self.assertEqual(result.returncode, 2, self.output(result))
        self.assertIn("[conflict] templates/remove.txt", result.stdout)
        self.assertIn("symbolic link 'templates'", result.stdout)
        self.assertEqual((external / "remove.txt").read_bytes(), b"outside target\n")

    def test_symlinked_manifest_is_rejected_before_it_is_read(self) -> None:
        manifest = self.fork.local / "scripts" / "template_manifest.json"
        external = self.fork.root / "external-manifest.json"
        external.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(external)

        result = self.fork.updater("check")

        self.assertEqual(result.returncode, 1, self.output(result))
        self.assertIn("Refusing to read scripts/template_manifest.json", result.stderr)
        self.assertIn("symbolic link", result.stderr)
        self.assertTrue(manifest.is_symlink())

    def test_symlinked_state_is_rejected_before_it_is_read(self) -> None:
        external = self.fork.root / "external-state.json"
        external.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "upstream_commit": None,
                    "managed_paths": [],
                }
            ),
            encoding="utf-8",
        )
        state = self.fork.local / ".agentic-sandbox-state.json"
        state.symlink_to(external)

        result = self.fork.updater("check")

        self.assertEqual(result.returncode, 1, self.output(result))
        self.assertIn("Refusing to read .agentic-sandbox-state.json", result.stderr)
        self.assertIn("symbolic link", result.stderr)
        self.assertTrue(state.is_symlink())
        self.assertIsNone(json.loads(external.read_text())["upstream_commit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
