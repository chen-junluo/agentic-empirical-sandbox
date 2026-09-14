#!/usr/bin/env python3
"""Validate build headers and generate the panel-factory dependency map."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PANEL_FACTORY_DIR = REPO_ROOT / "panel_factory"
OUTPUT_DOC = PANEL_FACTORY_DIR / "documents" / "pipeline_dependency_table.md"
HEADER_SCAN_LINES = 80
VALID_KINDS = {"intermediate", "feature", "panel"}
GENERATED_DATA_DIRS = {"data/features", "data/panels"}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DependencyError(RuntimeError):
    """A header or graph error that prevents a safe map update."""


@dataclass(frozen=True)
class Artifact:
    key: str
    kind: str
    grain: str
    merge_keys: tuple[str, ...]
    inputs: tuple[str, ...]
    output_path: str
    index_columns: tuple[str, ...]
    core_columns: tuple[str, ...]
    derived_columns: tuple[str, ...]
    logic: tuple[str, ...]
    built_by: str


def _required_match(pattern: str, text: str, field: str, source: str) -> str:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise DependencyError(
            f"{source}: expected exactly one {field} field, found {len(matches)}."
        )
    return matches[0].strip()


def _header_list(lines: list[str], field: str, source: str) -> tuple[str, ...]:
    heading = f"# {field}:"
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) != 1:
        raise DependencyError(
            f"{source}: expected exactly one {field} block, found {len(positions)}."
        )

    items: list[str] = []
    for line in lines[positions[0] + 1 :]:
        if line.strip() == "#":
            break
        match = re.match(r"^#\s+-\s+(.+?)\s*$", line)
        if not match:
            break
        items.append(match.group(1))
    if not items:
        raise DependencyError(f"{source}: {field} must contain at least one item.")
    return tuple(items)


def _split_columns(raw: str) -> tuple[str, ...]:
    if raw.lower() == "none":
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def parse_header(file_path: Path, panel_factory_dir: Path) -> Artifact:
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()[:HEADER_SCAN_LINES]
    except OSError as exc:
        raise DependencyError(f"Cannot read {file_path}: {exc}") from exc

    source = file_path.relative_to(panel_factory_dir.parent).as_posix()
    text = "\n".join(lines)
    artifact_value = _required_match(
        r"^# Artifact:\s*([^\s]+)\s*$", text, "Artifact", source
    )
    if "/" not in artifact_value:
        raise DependencyError(
            f"{source}: Artifact must use kind/artifact_key format."
        )
    kind, key = artifact_value.split("/", 1)
    grain = _required_match(r"^# Grain:\s*(.+?)\s*$", text, "Grain", source)
    merge_keys = _split_columns(
        _required_match(
            r"^# Merge Keys:\s*(.+?)\s*$", text, "Merge Keys", source
        )
    )
    output_path = _required_match(
        r"^# Output:\s*([^\s]+)\s*$", text, "Output", source
    )
    index_columns = _split_columns(
        _required_match(
            r"^#\s+- Index:\s*(.+?)\s*$", text, "Output Index", source
        )
    )
    core_columns = _split_columns(
        _required_match(
            r"^#\s+- Core:\s*(.+?)\s*$", text, "Output Core", source
        )
    )
    derived_columns = _split_columns(
        _required_match(
            r"^#\s+- Derived:\s*(.+?)\s*$", text, "Output Derived", source
        )
    )
    raw_inputs = _header_list(lines, "Inputs", source)
    inputs = tuple(item.split(" #", 1)[0].strip().split()[0] for item in raw_inputs)
    logic = _header_list(lines, "Logic", source)

    artifact = Artifact(
        key=key,
        kind=kind,
        grain=grain,
        merge_keys=merge_keys,
        inputs=inputs,
        output_path=output_path,
        index_columns=index_columns,
        core_columns=core_columns,
        derived_columns=derived_columns,
        logic=logic,
        built_by=source,
    )
    validate_artifact(artifact, file_path, panel_factory_dir)
    return artifact


def validate_artifact(
    artifact: Artifact,
    file_path: Path,
    panel_factory_dir: Path,
) -> None:
    source = artifact.built_by
    if artifact.kind not in VALID_KINDS:
        raise DependencyError(
            f"{source}: invalid artifact kind {artifact.kind!r}; "
            f"expected one of {sorted(VALID_KINDS)}."
        )
    if not NAME_PATTERN.fullmatch(artifact.key):
        raise DependencyError(f"{source}: invalid artifact key {artifact.key!r}.")
    if not NAME_PATTERN.fullmatch(artifact.grain):
        raise DependencyError(f"{source}: invalid grain {artifact.grain!r}.")
    if not artifact.merge_keys or not all(
        KEY_PATTERN.fullmatch(item) for item in artifact.merge_keys
    ):
        raise DependencyError(f"{source}: Merge Keys must be valid column names.")
    if artifact.index_columns != artifact.merge_keys:
        raise DependencyError(
            f"{source}: Output Index must exactly match Merge Keys."
        )
    if len(set(artifact.inputs)) != len(artifact.inputs):
        raise DependencyError(f"{source}: Inputs contains duplicate entries.")

    output = PurePosixPath(artifact.output_path)
    if output.is_absolute() or ".." in output.parts or output.suffix != ".csv":
        raise DependencyError(
            f"{source}: Output must be a repository-relative .csv path."
        )
    if output.stem != artifact.key:
        raise DependencyError(
            f"{source}: artifact key {artifact.key!r} must match output filename stem."
        )
    expected_dir = "data/panels" if artifact.kind == "panel" else "data/features"
    if output.parent.as_posix() != expected_dir:
        raise DependencyError(
            f"{source}: {artifact.kind} output must be under {expected_dir}/."
        )

    if artifact.kind == "feature" and not artifact.key.startswith(
        f"{artifact.grain}_"
    ):
        raise DependencyError(
            f"{source}: feature output must use {{grain}}_{{feature_name}}.csv."
        )
    if artifact.kind == "intermediate" and artifact.key != (
        f"{artifact.grain}_intermediate"
    ):
        raise DependencyError(
            f"{source}: intermediate output must use {{grain}}_intermediate.csv."
        )
    if artifact.kind == "panel" and not artifact.key.startswith(
        f"{artifact.grain}_"
    ):
        raise DependencyError(f"{source}: panel output must begin with its grain.")

    relative = file_path.relative_to(panel_factory_dir).parts
    expected_area = "features" if artifact.kind == "feature" else "panels"
    if len(relative) < 3 or relative[:2] != ("src", expected_area):
        raise DependencyError(
            f"{source}: {artifact.kind} builder must be under src/{expected_area}/."
        )


def discover_artifacts(panel_factory_dir: Path) -> list[Artifact]:
    build_files = sorted(
        list((panel_factory_dir / "src" / "features").rglob("build_*.py"))
        + list((panel_factory_dir / "src" / "panels").rglob("build_*.py"))
    )
    if not build_files:
        raise DependencyError("No build_*.py files were found under panel_factory/src/.")

    artifacts = [parse_header(path, panel_factory_dir) for path in build_files]
    by_key: dict[str, Artifact] = {}
    by_output: dict[str, Artifact] = {}
    for artifact in artifacts:
        if artifact.key in by_key:
            raise DependencyError(
                f"Duplicate artifact key {artifact.key!r}: "
                f"{by_key[artifact.key].built_by} and {artifact.built_by}."
            )
        if artifact.output_path in by_output:
            raise DependencyError(
                f"Duplicate output path {artifact.output_path!r}: "
                f"{by_output[artifact.output_path].built_by} and {artifact.built_by}."
            )
        by_key[artifact.key] = artifact
        by_output[artifact.output_path] = artifact
    return artifacts


def resolve_graph(
    artifacts: list[Artifact],
) -> tuple[
    list[Artifact],
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
    dict[str, tuple[str, ...]],
]:
    by_key = {artifact.key: artifact for artifact in artifacts}
    by_output = {artifact.output_path: artifact.key for artifact in artifacts}
    dependencies: dict[str, set[str]] = {artifact.key: set() for artifact in artifacts}
    external_inputs: dict[str, set[str]] = {artifact.key: set() for artifact in artifacts}

    for artifact in artifacts:
        for input_value in artifact.inputs:
            dependency = by_key.get(input_value)
            dependency_key = dependency.key if dependency else by_output.get(input_value)
            if dependency_key is None:
                input_path = PurePosixPath(input_value)
                stem_match = by_key.get(input_path.stem)
                dependency_key = stem_match.key if stem_match else None
            if dependency_key is not None:
                dependencies[artifact.key].add(dependency_key)
                continue
            if PurePosixPath(input_value).parent.as_posix() in GENERATED_DATA_DIRS:
                raise DependencyError(
                    f"{artifact.built_by}: generated input {input_value!r} does not "
                    "match any declared artifact."
                )
            external_inputs[artifact.key].add(input_value)

    downstream: dict[str, set[str]] = {artifact.key: set() for artifact in artifacts}
    indegree = {key: len(values) for key, values in dependencies.items()}
    for artifact_key, upstream_keys in dependencies.items():
        for upstream_key in upstream_keys:
            downstream[upstream_key].add(artifact_key)

    ready = sorted(key for key, count in indegree.items() if count == 0)
    ordered_keys: list[str] = []
    while ready:
        key = ready.pop(0)
        ordered_keys.append(key)
        for child in sorted(downstream[key]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered_keys) != len(artifacts):
        cycle_keys = sorted(key for key, count in indegree.items() if count > 0)
        raise DependencyError(
            "Artifact dependency cycle detected: " + ", ".join(cycle_keys)
        )

    def freeze(mapping: dict[str, set[str]]) -> dict[str, tuple[str, ...]]:
        return {key: tuple(sorted(values)) for key, values in mapping.items()}

    return (
        [by_key[key] for key in ordered_keys],
        freeze(dependencies),
        freeze(downstream),
        freeze(external_inputs),
    )


def _code_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _mermaid_label(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;")


def render_document(artifacts: list[Artifact]) -> str:
    ordered, dependencies, downstream, external_inputs = resolve_graph(artifacts)
    artifact_ids = {
        artifact.key: f"artifact_{index}" for index, artifact in enumerate(ordered)
    }
    source_values = sorted(
        {value for values in external_inputs.values() for value in values}
    )
    source_ids = {value: f"source_{index}" for index, value in enumerate(source_values)}

    counts = {
        kind: sum(artifact.kind == kind for artifact in ordered)
        for kind in ("intermediate", "feature", "panel")
    }
    lines = [
        "<!-- Auto-generated by scripts/update_dependency_docs.py. Do not edit by hand. -->",
        "# Pipeline Dependency Map",
        "",
        "This map is generated from the structured headers in `panel_factory/src/**/build_*.py`.",
        "Update a builder header first, then run `python3 scripts/update_dependency_docs.py write`.",
        "",
        "## Summary",
        "",
        f"- Artifacts: {len(ordered)}",
        f"- Intermediates: {counts['intermediate']}",
        f"- Features: {counts['feature']}",
        f"- Panels: {counts['panel']}",
        f"- External inputs: {len(source_values)}",
        "",
        "## Dependency graph",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for source in source_values:
        lines.append(f'  {source_ids[source]}["{_mermaid_label(source)}"]:::source')
    for artifact in ordered:
        label = _mermaid_label(
            f"{artifact.key}<br/>{artifact.kind} | {artifact.grain}"
        )
        lines.append(f'  {artifact_ids[artifact.key]}["{label}"]:::artifact')
    for artifact in ordered:
        for source in external_inputs[artifact.key]:
            lines.append(f"  {source_ids[source]} --> {artifact_ids[artifact.key]}")
        for dependency in dependencies[artifact.key]:
            lines.append(f"  {artifact_ids[dependency]} --> {artifact_ids[artifact.key]}")
    lines.extend(
        [
            "  classDef source fill:#f5f5f5,stroke:#777,stroke-dasharray:4 3;",
            "  classDef artifact fill:#eef6ff,stroke:#2563eb;",
            "```",
            "",
            "## Artifact table",
            "",
            "| artifact_key | kind | grain | merge_keys | inputs | downstream | output | built_by |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for artifact in ordered:
        row = [
            f"`{artifact.key}`",
            f"`{artifact.kind}`",
            f"`{artifact.grain}`",
            _code_list(artifact.merge_keys),
            _code_list(artifact.inputs),
            _code_list(downstream[artifact.key]),
            f"`{artifact.output_path}`",
            f"`{artifact.built_by}`",
        ]
        lines.append("| " + " | ".join(_table_cell(value) for value in row) + " |")

    lines.extend(["", "## Artifact contracts", ""])
    for artifact in ordered:
        lines.extend(
            [
                f"### `{artifact.key}`",
                "",
                f"- Kind: `{artifact.kind}`",
                f"- Grain: `{artifact.grain}`",
                f"- Merge keys: {_code_list(artifact.merge_keys)}",
                f"- Inputs: {_code_list(artifact.inputs)}",
                f"- Output: `{artifact.output_path}`",
                f"- Builder: `{artifact.built_by}`",
                "- Output columns:",
                f"  - Index: {_code_list(artifact.index_columns)}",
                f"  - Core: {_code_list(artifact.core_columns)}",
                f"  - Derived: {_code_list(artifact.derived_columns)}",
                "- Logic:",
            ]
        )
        lines.extend(f"  - {item}" for item in artifact.logic)
        lines.append("")

    if source_values:
        lines.extend(["## External inputs", ""])
        lines.extend(f"- `{source}`" for source in source_values)
        lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".dependency-map-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate build headers and check or write the dependency map."
    )
    parser.add_argument(
        "command", nargs="?", choices=("check", "write"), default="write"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        artifacts = discover_artifacts(PANEL_FACTORY_DIR)
        content = render_document(artifacts)
        current = OUTPUT_DOC.read_text(encoding="utf-8") if OUTPUT_DOC.exists() else None
        if args.command == "check":
            if current != content:
                print(
                    "Dependency map is stale. Run: "
                    "python3 scripts/update_dependency_docs.py write",
                    file=sys.stderr,
                )
                return 1
            print(f"Dependency map is current: {OUTPUT_DOC.relative_to(REPO_ROOT)}")
            return 0

        if current == content:
            print(f"Dependency map already current: {OUTPUT_DOC.relative_to(REPO_ROOT)}")
            return 0
        atomic_write(OUTPUT_DOC, content)
        print(
            f"Generated {OUTPUT_DOC.relative_to(REPO_ROOT)} "
            f"from {len(artifacts)} builder header(s)."
        )
        return 0
    except (DependencyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
