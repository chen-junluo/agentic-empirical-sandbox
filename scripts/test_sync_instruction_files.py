#!/usr/bin/env python3
"""Integration tests for sync_instruction_files.py using temporary Git repositories."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync_instruction_files.py").resolve()
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


class TemporaryRepositories:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="instruction-sync-test-")
        self.root = Path(self.temporary.name)
        self.upstream = self.root / "upstream"
        self.local = self.root / "local"
        self.upstream.mkdir()
        run(["git", "init", "-q", "-b", "main"], self.upstream)
        run(["git", "config", "user.email", "test@example.com"], self.upstream)
        run(["git", "config", "user.name", "Sync Test"], self.upstream)

        self.paths = ["AGENTS.md", "archive/AGENTS.md", "projects/CLAUDE.md"]
        files = []
        for index, relative in enumerate(self.paths):
            self.write_upstream(relative, self.upstream_content(index, 1))
            files.append({"path": relative, "type": "instruction"})
        self.write_upstream(
            "scripts/template_manifest.json",
            json.dumps({"schema_version": 1, "files": files}, indent=2) + "\n",
        )
        self.commit_upstream("baseline")

        run(["git", "clone", "-q", str(self.upstream), str(self.local)], self.root)
        run(["git", "remote", "rename", "origin", "upstream"], self.local)
        run(["git", "config", "user.email", "test@example.com"], self.local)
        run(["git", "config", "user.name", "Sync Test"], self.local)

    def close(self) -> None:
        self.temporary.cleanup()

    def upstream_content(self, index: int, version: int) -> str:
        return (
            f"# Public rules {index} v{version}\n\n"
            f"## User-Specific Rules\n\n"
            f"<!-- upstream comment style {index}-{version} -->\n"
        )

    def local_suffix(self, index: int) -> bytes:
        if index == 0:
            return (
                f"{MARKER}  \r\n\r\n"
                "<!-- 用户注释格式可以各不相同 -->\r\n"
                "- local rule alpha\r\n"
            ).encode("utf-8")
        return (
            f"{MARKER}\n\n<!-- 自定义注释 {index} -->\n- local rule {index}\n"
        ).encode("utf-8")

    def write_upstream(self, relative: str, content: str | bytes) -> None:
        path = self.upstream / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

    def commit_upstream(self, message: str) -> None:
        run(["git", "add", "-A"], self.upstream)
        run(["git", "commit", "-q", "-m", message], self.upstream)

    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run(
            [
                sys.executable,
                str(SCRIPT),
                "--source-url",
                str(self.upstream),
                *args,
            ],
            self.local,
            check=False,
        )


class SyncInstructionFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repos = TemporaryRepositories()

    def tearDown(self) -> None:
        self.repos.close()

    def test_sync_replaces_prefix_and_preserves_each_local_suffix(self) -> None:
        expected_suffixes: dict[str, bytes] = {}
        for index, relative in enumerate(self.repos.paths):
            old_local_prefix = f"# Locally edited rules {index}\n\n".encode("utf-8")
            suffix = self.repos.local_suffix(index)
            expected_suffixes[relative] = suffix
            (self.repos.local / relative).write_bytes(old_local_prefix + suffix)
            self.repos.write_upstream(
                relative, self.repos.upstream_content(index, 2)
            )
        self.repos.commit_upstream("update public instruction rules")
        unlisted = self.repos.local / "projects/private/AGENTS.md"
        unlisted.parent.mkdir(parents=True)
        unlisted.write_text("private rules\n", encoding="utf-8")

        result = self.repos.invoke()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Synchronized 3 instruction file(s).", result.stdout)
        for index, relative in enumerate(self.repos.paths):
            updated = (self.repos.local / relative).read_bytes()
            expected_prefix = f"# Public rules {index} v2\n\n".encode("utf-8")
            self.assertTrue(updated.startswith(expected_prefix))
            self.assertEqual(updated[len(expected_prefix) :], expected_suffixes[relative])
        self.assertEqual(unlisted.read_text(encoding="utf-8"), "private rules\n")

        repeated = self.repos.invoke()
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertIn("Synchronized 0 instruction file(s).", repeated.stdout)

    def test_check_reports_without_writing(self) -> None:
        relative = self.repos.paths[0]
        before = (self.repos.local / relative).read_bytes()
        self.repos.write_upstream(relative, self.repos.upstream_content(0, 2))
        self.repos.commit_upstream("update one instruction")

        result = self.repos.invoke("--check")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[update] AGENTS.md", result.stdout)
        self.assertEqual((self.repos.local / relative).read_bytes(), before)

    def test_invalid_marker_aborts_all_writes(self) -> None:
        first, second = self.repos.paths[:2]
        before_first = (self.repos.local / first).read_bytes()
        (self.repos.local / second).write_text("# Missing marker\n", encoding="utf-8")
        self.repos.write_upstream(first, self.repos.upstream_content(0, 2))
        self.repos.commit_upstream("update beside malformed local file")

        result = self.repos.invoke()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[conflict] archive/AGENTS.md", result.stdout)
        self.assertIn("No working-tree files were changed.", result.stdout)
        self.assertEqual((self.repos.local / first).read_bytes(), before_first)

    def test_missing_upstream_marker_aborts_all_writes(self) -> None:
        first, second = self.repos.paths[:2]
        before_first = (self.repos.local / first).read_bytes()
        self.repos.write_upstream(first, self.repos.upstream_content(0, 2))
        self.repos.write_upstream(second, "# No boundary\n")
        self.repos.commit_upstream("publish malformed instruction")

        result = self.repos.invoke()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[conflict] archive/AGENTS.md", result.stdout)
        self.assertEqual((self.repos.local / first).read_bytes(), before_first)

    def test_duplicate_local_marker_aborts_all_writes(self) -> None:
        first, second = self.repos.paths[:2]
        before_first = (self.repos.local / first).read_bytes()
        (self.repos.local / second).write_text(
            f"# Local rules\n\n{MARKER}\n\nlocal suffix\n\n{MARKER}\n",
            encoding="utf-8",
        )
        self.repos.write_upstream(first, self.repos.upstream_content(0, 2))
        self.repos.commit_upstream("update beside duplicate marker")

        result = self.repos.invoke()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("[conflict] archive/AGENTS.md", result.stdout)
        self.assertIn("2 exact markers", result.stdout)
        self.assertEqual((self.repos.local / first).read_bytes(), before_first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
