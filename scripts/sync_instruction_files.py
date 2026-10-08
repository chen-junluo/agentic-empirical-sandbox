#!/usr/bin/env python3
"""Replace managed instruction prefixes with the latest public GitHub versions."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from update_template import (
    ManagedFile,
    UpdateError,
    find_repo_root,
    git,
    git_file,
    instruction_parts,
    load_manifest,
    local_file,
)


UPSTREAM_URL = "https://github.com/chen-junluo/agentic-empirical-sandbox.git"
UPSTREAM_BRANCH = "main"


@dataclass
class SyncPlan:
    managed: ManagedFile
    status: str
    detail: str
    replacement: bytes | None = None


def fetch_latest(repo_root: Path, source_url: str) -> str:
    print(f"Fetching {source_url} ({UPSTREAM_BRANCH})...")
    result = subprocess.run(
        ["git", "fetch", "--quiet", source_url, UPSTREAM_BRANCH],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise UpdateError(f"Could not fetch the latest public template: {detail}")
    fetched = git(repo_root, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    return fetched.stdout.decode("ascii").strip()


def analyze(repo_root: Path, source_url: str) -> tuple[str, list[SyncPlan]]:
    managed_files = [
        item for item in load_manifest(repo_root) if item.file_type == "instruction"
    ]
    if not managed_files:
        raise UpdateError("The local manifest contains no managed instruction files.")

    latest_commit = fetch_latest(repo_root, source_url)
    plans: list[SyncPlan] = []
    for managed in managed_files:
        local, local_error = local_file(repo_root, managed.path)
        if local_error:
            plans.append(SyncPlan(managed, "conflict", local_error))
            continue

        upstream = git_file(repo_root, latest_commit, managed.path)
        if upstream is None:
            plans.append(
                SyncPlan(
                    managed,
                    "manual review",
                    "not present upstream; local file will not be deleted",
                )
            )
            continue

        try:
            upstream_prefix, _ = instruction_parts(
                upstream, managed.path, "upstream"
            )
            if local is None:
                replacement = upstream
            else:
                _, local_suffix = instruction_parts(local, managed.path, "local")
                replacement = upstream_prefix + local_suffix
        except UpdateError as exc:
            plans.append(SyncPlan(managed, "conflict", str(exc)))
            continue

        if local == replacement:
            plans.append(SyncPlan(managed, "unchanged", "already matches latest rules"))
        else:
            plans.append(
                SyncPlan(
                    managed,
                    "update",
                    "replace public rules and preserve the local user-specific suffix",
                    replacement,
                )
            )
    return latest_commit, plans


def print_report(commit: str, plans: list[SyncPlan]) -> None:
    print(f"Upstream commit: {commit}")
    print("Managed instruction files:")
    for plan in plans:
        print(f"  [{plan.status}] {plan.managed.path} - {plan.detail}")


def stage_file(destination: Path, content: bytes) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".sync-instructions-", dir=destination.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            os.chmod(temporary, destination.stat().st_mode & 0o777)
        else:
            os.chmod(temporary, 0o644)
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def apply_plans(repo_root: Path, plans: list[SyncPlan]) -> int:
    problems = [plan for plan in plans if plan.status in {"conflict", "manual review"}]
    if problems:
        print("Sync aborted: review the listed files before retrying.")
        print("No working-tree files were changed.")
        return 2

    updates = [plan for plan in plans if plan.status == "update"]
    staged: list[tuple[Path, Path]] = []
    try:
        for plan in updates:
            assert plan.replacement is not None
            destination = repo_root.joinpath(*PurePosixPath(plan.managed.path).parts)
            staged.append((stage_file(destination, plan.replacement), destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    except OSError as exc:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        raise UpdateError(f"Atomic file write failed: {exc}") from exc

    print(f"Synchronized {len(updates)} instruction file(s).")
    print("Review the result with: git diff")
    print("No commit was created.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch canonical GitHub instruction files, replace their public-rule "
            "prefixes, and preserve local User-Specific Rules sections."
        )
    )
    parser.add_argument(
        "--source-url",
        default=UPSTREAM_URL,
        help="Git repository URL to fetch (defaults to the canonical public template)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fetch and report planned changes without writing files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repo_root = find_repo_root()
        commit, plans = analyze(repo_root, args.source_url)
        print_report(commit, plans)
        if args.check:
            if any(plan.status in {"conflict", "manual review"} for plan in plans):
                print("Check found files requiring review; no files were changed.")
                return 2
            print("Check completed; no files were changed.")
            return 0
        return apply_plans(repo_root, plans)
    except UpdateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
