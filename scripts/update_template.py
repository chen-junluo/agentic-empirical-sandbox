#!/usr/bin/env python3
"""Safely preview and apply allowlisted updates from upstream/main."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional


UPSTREAM_REMOTE = "upstream"
UPSTREAM_BRANCH = "main"
UPSTREAM_REF = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
MANIFEST_PATH = Path("scripts/template_manifest.json")
STATE_PATH = Path(".agentic-sandbox-state.json")
MARKER = b"## User-Specific Rules"
VALID_TYPES = {"file", "instruction", "placeholder"}
STATUS_ORDER = {
    "conflict": 0,
    "safe update": 1,
    "add": 2,
    "manual review": 3,
    "protected": 4,
    "unchanged": 5,
}


class UpdateError(RuntimeError):
    """A preflight error that prevents a safe update."""


@dataclass(frozen=True)
class ManagedFile:
    path: str
    file_type: str


@dataclass
class FilePlan:
    managed: ManagedFile
    status: str
    detail: str
    new_content: Optional[bytes] = None


@dataclass(frozen=True)
class UpdaterState:
    upstream_commit: Optional[str]
    managed_paths: Optional[frozenset[str]]


@dataclass
class Analysis:
    repo_root: Path
    baseline_commit: str
    upstream_commit: str
    managed_files: list[ManagedFile]
    plans: list[FilePlan]

    @property
    def has_conflicts(self) -> bool:
        return any(plan.status == "conflict" for plan in self.plans)


def git(
    repo_root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise UpdateError(f"git {' '.join(args)} failed: {message}")
    return result


def find_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise UpdateError("Run this command from inside the sandbox Git repository.")
    return Path(result.stdout.decode("utf-8").strip()).resolve()


def validate_manifest_path(repo_root: Path, raw_path: object) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise UpdateError("Every manifest path must be a non-empty string.")
    posix_path = PurePosixPath(raw_path)
    if (
        not posix_path.parts
        or posix_path.is_absolute()
        or ".." in posix_path.parts
        or "." in posix_path.parts
        or posix_path.parts[0] == ".git"
        or any(char in raw_path for char in "*?[]")
    ):
        raise UpdateError(f"Unsafe manifest path: {raw_path!r}")

    return posix_path.as_posix()


def load_manifest(repo_root: Path) -> list[ManagedFile]:
    path = repo_root / MANIFEST_PATH
    linked_component = symlink_component(repo_root, MANIFEST_PATH.as_posix())
    if linked_component is not None:
        raise UpdateError(
            f"Refusing to read {MANIFEST_PATH}: path uses symbolic link "
            f"{linked_component!r}."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UpdateError(f"Missing manifest: {MANIFEST_PATH.as_posix()}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Cannot read {MANIFEST_PATH.as_posix()}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise UpdateError("template_manifest.json must use schema_version 1.")
    entries = payload.get("files")
    if not isinstance(entries, list):
        raise UpdateError("template_manifest.json must contain a files list.")

    managed_files: list[ManagedFile] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise UpdateError("Each manifest entry must be an object.")
        path_value = validate_manifest_path(repo_root, entry.get("path"))
        file_type = entry.get("type")
        if file_type not in VALID_TYPES:
            raise UpdateError(
                f"Invalid type for {path_value}: expected one of {sorted(VALID_TYPES)}."
            )
        if path_value in seen:
            raise UpdateError(f"Duplicate manifest path: {path_value}")
        if path_value == STATE_PATH.as_posix():
            raise UpdateError(f"{STATE_PATH} is updater state, not managed template content.")
        seen.add(path_value)
        managed_files.append(ManagedFile(path_value, file_type))
    return managed_files


def read_state(repo_root: Path) -> UpdaterState:
    path = repo_root / STATE_PATH
    linked_component = symlink_component(repo_root, STATE_PATH.as_posix())
    if linked_component is not None:
        raise UpdateError(
            f"Refusing to read {STATE_PATH}: path uses symbolic link "
            f"{linked_component!r}."
        )
    if not path.exists():
        return UpdaterState(None, None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Cannot read {STATE_PATH}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise UpdateError(f"{STATE_PATH} must use schema_version 1.")
    commit = payload.get("upstream_commit")
    if commit is not None and (not isinstance(commit, str) or not commit.strip()):
        raise UpdateError(f"{STATE_PATH} has an invalid upstream_commit.")
    raw_paths = payload.get("managed_paths")
    managed_paths: Optional[frozenset[str]] = None
    if raw_paths is not None:
        if not isinstance(raw_paths, list) or not all(
            isinstance(item, str) for item in raw_paths
        ):
            raise UpdateError(f"{STATE_PATH} has an invalid managed_paths list.")
        managed_paths = frozenset(raw_paths)
    return UpdaterState(commit, managed_paths)


def ensure_upstream(repo_root: Path) -> None:
    result = git(repo_root, "remote", "get-url", UPSTREAM_REMOTE, check=False)
    if result.returncode != 0:
        raise UpdateError(
            "Remote 'upstream' is not configured.\n"
            "After confirming the public repository URL, add it with:\n"
            "  git remote add upstream CONFIRMED_PUBLIC_REPOSITORY_URL\n"
            "Then rerun this command. The updater will not add a remote automatically."
        )


def fetch_upstream(repo_root: Path) -> str:
    print(f"Fetching {UPSTREAM_REF}...")
    git(repo_root, "fetch", "--quiet", UPSTREAM_REMOTE, UPSTREAM_BRANCH)
    result = git(repo_root, "rev-parse", "--verify", f"{UPSTREAM_REF}^{{commit}}")
    return result.stdout.decode("ascii").strip()


def resolve_baseline(
    repo_root: Path,
    state_commit: Optional[str],
    upstream_commit: str,
) -> str:
    if state_commit:
        result = git(repo_root, "cat-file", "-e", f"{state_commit}^{{commit}}", check=False)
        if result.returncode != 0:
            raise UpdateError(
                f"The recorded baseline commit {state_commit} is unavailable. "
                "Fetch the missing history or repair the state file after manual review."
            )
        return state_commit

    result = git(repo_root, "merge-base", "HEAD", upstream_commit, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise UpdateError(
            "No recorded baseline and no merge base with upstream/main. "
            "Manual review is required before the first update."
        )
    return result.stdout.decode("ascii").strip()


def git_file(repo_root: Path, commit: str, path: str) -> Optional[bytes]:
    object_name = f"{commit}:{path}"
    if git(repo_root, "cat-file", "-e", object_name, check=False).returncode != 0:
        return None
    return git(repo_root, "show", object_name).stdout


def symlink_component(repo_root: Path, path: str) -> Optional[str]:
    """Return the first symlink in a repository-relative path, if any."""
    candidate = repo_root
    for part in PurePosixPath(path).parts:
        candidate /= part
        if candidate.is_symlink():
            return candidate.relative_to(repo_root).as_posix()
    return None


def local_file(repo_root: Path, path: str) -> tuple[Optional[bytes], Optional[str]]:
    candidate = repo_root.joinpath(*PurePosixPath(path).parts)
    linked_component = symlink_component(repo_root, path)
    if linked_component is not None:
        return None, (
            f"local path uses symbolic link {linked_component!r}; "
            "symlink synchronization is unsupported"
        )
    if not candidate.exists():
        return None, None
    if candidate.is_dir():
        return None, "local path is a directory, not a file"
    try:
        return candidate.read_bytes(), None
    except OSError as exc:
        return None, f"cannot read local file: {exc}"


def instruction_parts(content: bytes, path: str, version: str) -> tuple[bytes, bytes]:
    lines = content.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        if line.rstrip(b"\r\n").rstrip(b" \t") == MARKER:
            offsets.append(cursor)
        cursor += len(line)
    if len(offsets) != 1:
        raise UpdateError(
            f"{path} has {len(offsets)} exact markers in {version}; expected exactly 1."
        )
    offset = offsets[0]
    return content[:offset], content[offset:]


def managed_content(
    managed: ManagedFile,
    content: Optional[bytes],
    version: str,
) -> Optional[bytes]:
    if content is None:
        return None
    if managed.file_type != "instruction":
        return content
    prefix, _ = instruction_parts(content, managed.path, version)
    return prefix


def build_replacement(
    managed: ManagedFile,
    upstream_content: bytes,
    local_content: Optional[bytes],
) -> bytes:
    if managed.file_type != "instruction" or local_content is None:
        return upstream_content
    upstream_prefix, _ = instruction_parts(upstream_content, managed.path, "upstream")
    _, local_user_section = instruction_parts(local_content, managed.path, "local")
    return upstream_prefix + local_user_section


def plan_file(
    managed: ManagedFile,
    baseline: Optional[bytes],
    local: Optional[bytes],
    upstream: Optional[bytes],
    local_error: Optional[str],
) -> FilePlan:
    if local_error:
        return FilePlan(managed, "conflict", local_error)

    try:
        baseline_managed = managed_content(managed, baseline, "baseline")
        local_managed = managed_content(managed, local, "local")
        upstream_managed = managed_content(managed, upstream, "upstream")
    except UpdateError as exc:
        return FilePlan(managed, "conflict", str(exc))

    if baseline is not None and upstream is None:
        return FilePlan(
            managed,
            "manual review",
            "removed or renamed upstream; the local path will not be deleted",
        )

    if baseline is None and upstream is not None:
        if local is None:
            return FilePlan(
                managed,
                "add",
                "new allowlisted upstream file",
                build_replacement(managed, upstream, local),
            )
        if local_managed == upstream_managed:
            return FilePlan(managed, "unchanged", "already matches the upstream addition")
        return FilePlan(
            managed,
            "protected",
            "path already exists locally; it will not be overwritten",
        )

    if baseline is None and upstream is None:
        if local is None:
            return FilePlan(managed, "unchanged", "not present in baseline or upstream")
        return FilePlan(managed, "protected", "local-only file; upstream has no version")

    assert baseline_managed is not None and upstream_managed is not None
    upstream_changed = upstream_managed != baseline_managed

    if not upstream_changed:
        if local is None:
            return FilePlan(managed, "protected", "deleted locally; upstream is unchanged")
        if local_managed == baseline_managed:
            return FilePlan(managed, "unchanged", "managed content matches the baseline")
        return FilePlan(managed, "protected", "local managed content changed; upstream is unchanged")

    if local is not None and local_managed == upstream_managed:
        return FilePlan(managed, "unchanged", "managed content already matches upstream")
    if local is not None and local_managed == baseline_managed:
        return FilePlan(
            managed,
            "safe update",
            "upstream changed and local managed content still matches the baseline",
            build_replacement(managed, upstream, local),
        )
    return FilePlan(
        managed,
        "conflict",
        "local and upstream managed content both changed relative to the baseline",
    )


def analyze(repo_root: Path) -> Analysis:
    managed_files = load_manifest(repo_root)
    ensure_upstream(repo_root)
    state = read_state(repo_root)
    upstream_commit = fetch_upstream(repo_root)
    baseline_commit = resolve_baseline(repo_root, state.upstream_commit, upstream_commit)

    plans: list[FilePlan] = []
    for managed in managed_files:
        newly_managed = (
            state.upstream_commit is not None
            and state.managed_paths is not None
            and managed.path not in state.managed_paths
        )
        baseline = None if newly_managed else git_file(
            repo_root, baseline_commit, managed.path
        )
        upstream = git_file(repo_root, upstream_commit, managed.path)
        local, local_error = local_file(repo_root, managed.path)
        plans.append(plan_file(managed, baseline, local, upstream, local_error))
    return Analysis(
        repo_root,
        baseline_commit,
        upstream_commit,
        managed_files,
        plans,
    )


def print_report(analysis: Analysis) -> None:
    print(f"Baseline: {analysis.baseline_commit}")
    print(f"Upstream: {analysis.upstream_commit}")
    print("Managed file report:")
    for plan in sorted(
        analysis.plans,
        key=lambda item: (STATUS_ORDER[item.status], item.managed.path),
    ):
        print(f"  [{plan.status}] {plan.managed.path} - {plan.detail}")
    print("  [protected] all paths outside the local manifest - not scanned or modified")

    counts: dict[str, int] = {}
    for plan in analysis.plans:
        counts[plan.status] = counts.get(plan.status, 0) + 1
    summary = ", ".join(
        f"{status}: {counts[status]}" for status in STATUS_ORDER if counts.get(status)
    )
    print(f"Summary: {summary or 'no managed files'}")


def state_content(upstream_commit: str, managed_files: list[ManagedFile]) -> bytes:
    return (
        json.dumps(
            {
                "schema_version": 1,
                "upstream_commit": upstream_commit,
                "managed_paths": sorted(item.path for item in managed_files),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def stage_atomic_file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".update-template-", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists() and not path.is_symlink():
            os.chmod(temp_path, path.stat().st_mode & 0o777)
        else:
            os.chmod(temp_path, 0o644)
        return temp_path
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def apply_updates(analysis: Analysis) -> int:
    if analysis.has_conflicts:
        print("Apply aborted: conflicts or invalid instruction markers were found.")
        print("No working-tree files or updater state were changed.")
        return 2

    replacements: list[tuple[Path, bytes]] = []
    for plan in analysis.plans:
        if plan.status in {"safe update", "add"}:
            assert plan.new_content is not None
            replacements.append(
                (
                    analysis.repo_root.joinpath(*PurePosixPath(plan.managed.path).parts),
                    plan.new_content,
                )
            )
    replacements.append(
        (
            analysis.repo_root / STATE_PATH,
            state_content(analysis.upstream_commit, analysis.managed_files),
        )
    )

    staged: list[tuple[Path, Path]] = []
    try:
        for destination, content in replacements:
            staged.append((stage_atomic_file(destination, content), destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    except OSError as exc:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        raise UpdateError(f"Atomic write failed: {exc}") from exc

    updated_count = sum(
        plan.status in {"safe update", "add"} for plan in analysis.plans
    )
    print(f"Applied {updated_count} managed file update(s).")
    print(f"Recorded upstream commit {analysis.upstream_commit} in {STATE_PATH}.")
    print("Review the result with: git diff")
    print("No commit was created.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or apply safe allowlisted updates from upstream/main."
    )
    parser.add_argument("command", choices=("check", "apply"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        analysis = analyze(find_repo_root())
        print_report(analysis)
        if args.command == "check":
            if analysis.has_conflicts:
                print("Check completed with conflicts; apply would make no changes.")
                return 2
            print("Check completed without conflicts; the working tree was not changed.")
            return 0
        return apply_updates(analysis)
    except UpdateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
