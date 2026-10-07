#!/usr/bin/env python3
"""Validate ``PIPELINE_SPEC`` metadata and generate the dependency table.

Builder files are parsed with :mod:`ast` so documentation generation never
imports a builder or executes pipeline code.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PANEL_FACTORY_DIR = REPO_ROOT / "panel_factory"
PATHS_FILE_NAME = "src/utils/paths.py"
OUTPUT_DOC = PANEL_FACTORY_DIR / "documents" / "pipeline_dependency_table.md"
HEADER_SCAN_LINES = 80
VALID_STAGES = {"feature", "intermediate", "panel"}
REQUIRED_FIELDS = (
    "builder_name",
    "stage",
    "grain",
    "summary",
    "reads_raw",
    "reads_features",
    "reads_panels",
    "writes_features",
    "writes_panels",
    "merge_keys",
    "depends_on_builders",
)
OPTIONAL_FIELDS = ("notes", "contracts", "downstream_consumers")
LIST_FIELDS = (
    "reads_raw",
    "reads_features",
    "reads_panels",
    "writes_features",
    "writes_panels",
    "merge_keys",
    "depends_on_builders",
    "notes",
    "contracts",
    "downstream_consumers",
)
REGISTRY_NAMES = ("RAW_FILES", "FEATURE_OUTPUTS", "PANEL_OUTPUTS")


class DependencyError(RuntimeError):
    """A syntax or filesystem error that prevents metadata inspection."""


@dataclass(frozen=True)
class PipelineSpec:
    builder_name: str
    stage: str
    grain: str
    summary: str
    reads_raw: tuple[str, ...]
    reads_features: tuple[str, ...]
    reads_panels: tuple[str, ...]
    writes_features: tuple[str, ...]
    writes_panels: tuple[str, ...]
    merge_keys: tuple[str, ...]
    depends_on_builders: tuple[str, ...]
    notes: tuple[str, ...]
    contracts: tuple[str, ...]
    downstream_consumers: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class Registry:
    raw_files: frozenset[str]
    feature_outputs: frozenset[str]
    panel_outputs: frozenset[str]


def _warning(warnings: list[str], source: str, message: str) -> None:
    warnings.append(f"{source}: warning: {message}")


def _literal_assignment(tree: ast.Module, name: str, source: str) -> Any:
    assignments: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            assignments.append(node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                assignments.append(node)
    if len(assignments) != 1:
        raise DependencyError(
            f"{source}: expected exactly one top-level {name}, found {len(assignments)}."
        )
    node = assignments[0]
    value = node.value  # type: ignore[attr-defined]
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise DependencyError(
            f"{source}: {name} must be a literal Python value for AST extraction."
        ) from exc


def _parse_tree(path: Path, source: str) -> ast.Module:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DependencyError(f"Cannot read {source}: {exc}") from exc
    try:
        return ast.parse(text, filename=source)
    except SyntaxError as exc:
        raise DependencyError(f"{source}: invalid Python syntax: {exc}") from exc


def _string_list(
    value: Any,
    field: str,
    source: str,
    warnings: list[str],
) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        _warning(warnings, source, f"{field} must be a list of strings.")
        return None
    return tuple(value)


def _load_registry(panel_factory_dir: Path, warnings: list[str]) -> Registry:
    path = panel_factory_dir / PATHS_FILE_NAME
    source = path.relative_to(panel_factory_dir.parent).as_posix()
    try:
        tree = _parse_tree(path, source)
        values = {
            name: _literal_assignment(tree, name, source) for name in REGISTRY_NAMES
        }
    except (DependencyError, OSError) as exc:
        _warning(warnings, source, str(exc))
        return Registry(frozenset(), frozenset(), frozenset())

    result: dict[str, frozenset[str]] = {}
    for name, value in values.items():
        if not isinstance(value, dict) or not all(
            isinstance(key, str) for key in value
        ):
            _warning(warnings, source, f"{name} must be a dictionary keyed by artifact names.")
            result[name] = frozenset()
        else:
            result[name] = frozenset(value)
    return Registry(
        raw_files=result["RAW_FILES"],
        feature_outputs=result["FEATURE_OUTPUTS"],
        panel_outputs=result["PANEL_OUTPUTS"],
    )


def _extract_spec(
    path: Path,
    panel_factory_dir: Path,
    warnings: list[str],
) -> PipelineSpec | None:
    source = path.relative_to(panel_factory_dir.parent).as_posix()
    try:
        tree = _parse_tree(path, source)
        assignment_nodes = [
            node
            for node in tree.body
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "PIPELINE_SPEC"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "PIPELINE_SPEC"
            )
        ]
        if len(assignment_nodes) != 1:
            _warning(
                warnings,
                source,
                "expected exactly one top-level PIPELINE_SPEC assignment.",
            )
            return None
        assignment = assignment_nodes[0]
        if assignment.lineno > HEADER_SCAN_LINES:
            _warning(
                warnings,
                source,
                f"PIPELINE_SPEC must be near the top of the file (line <= {HEADER_SCAN_LINES}).",
            )
            return None
        raw_spec = ast.literal_eval(assignment.value)  # type: ignore[attr-defined]
    except (DependencyError, ValueError, TypeError, SyntaxError) as exc:
        _warning(warnings, source, str(exc))
        return None

    if not isinstance(raw_spec, dict):
        _warning(warnings, source, "PIPELINE_SPEC must be a dictionary.")
        return None

    missing = [field for field in REQUIRED_FIELDS if field not in raw_spec]
    if missing:
        _warning(warnings, source, f"PIPELINE_SPEC is missing fields: {', '.join(missing)}.")
        return None

    unknown = sorted(set(raw_spec) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        _warning(warnings, source, f"unknown PIPELINE_SPEC fields: {', '.join(unknown)}.")

    scalar_fields = ("builder_name", "stage", "grain", "summary")
    if not all(isinstance(raw_spec[field], str) for field in scalar_fields):
        _warning(warnings, source, "builder_name, stage, grain, and summary must be strings.")
        return None
    values: dict[str, tuple[str, ...]] = {}
    for field in LIST_FIELDS:
        parsed = _string_list(raw_spec.get(field, []), field, source, warnings)
        if parsed is None:
            return None
        values[field] = parsed

    return PipelineSpec(
        builder_name=raw_spec["builder_name"],
        stage=raw_spec["stage"],
        grain=raw_spec["grain"],
        summary=raw_spec["summary"],
        reads_raw=values["reads_raw"],
        reads_features=values["reads_features"],
        reads_panels=values["reads_panels"],
        writes_features=values["writes_features"],
        writes_panels=values["writes_panels"],
        merge_keys=values["merge_keys"],
        depends_on_builders=values["depends_on_builders"],
        notes=values["notes"],
        contracts=values["contracts"],
        downstream_consumers=values["downstream_consumers"],
        source=source,
    )


def _validate_spec(
    spec: PipelineSpec,
    path: Path,
    panel_factory_dir: Path,
    registry: Registry,
    warnings: list[str],
) -> None:
    source = spec.source
    expected_builder = path.stem
    if spec.builder_name != expected_builder:
        _warning(warnings, source, f"builder_name must match filename stem {expected_builder!r}.")
    if spec.stage not in VALID_STAGES:
        _warning(warnings, source, f"stage {spec.stage!r} is invalid; use feature, intermediate, or panel.")
    area = path.relative_to(panel_factory_dir).parts[:2]
    expected_area = ("src", "features") if spec.stage == "feature" else ("src", "panels")
    if spec.stage in VALID_STAGES and area != expected_area:
        _warning(warnings, source, f"stage {spec.stage!r} does not match directory src/{area[1]}.")
    if not spec.summary.strip() or not spec.summary.strip().endswith("."):
        _warning(warnings, source, "summary should be one sentence ending with a period.")
    for field, allowed in (
        ("reads_raw", registry.raw_files),
        ("reads_features", registry.feature_outputs),
        ("writes_features", registry.feature_outputs),
        ("reads_panels", registry.panel_outputs),
        ("writes_panels", registry.panel_outputs),
    ):
        for key in getattr(spec, field):
            if key not in allowed:
                _warning(warnings, source, f"{field} contains unknown canonical artifact key {key!r}.")
    for key in spec.merge_keys:
        if not key or not (key[0].isalpha() or key[0] == "_") or not all(
            char.isalnum() or char == "_" for char in key
        ):
            _warning(warnings, source, f"merge_keys contains invalid column name {key!r}.")
    expected_feature_output = spec.stage in {"feature", "intermediate"}
    if expected_feature_output and not spec.writes_features:
        _warning(warnings, source, f"{spec.stage} builder must declare writes_features.")
    if expected_feature_output and spec.writes_panels:
        _warning(warnings, source, f"{spec.stage} builder must not declare writes_panels.")
    if spec.stage == "panel" and not spec.writes_panels:
        _warning(warnings, source, "panel builder must declare writes_panels.")
    if spec.stage == "panel" and spec.writes_features:
        _warning(warnings, source, "panel builder must not declare writes_features.")


def discover_specs(
    panel_factory_dir: Path,
    warnings: list[str] | None = None,
) -> list[PipelineSpec]:
    """Discover builders and return specs, collecting non-fatal warnings."""

    collected = warnings if warnings is not None else []
    registry = _load_registry(panel_factory_dir, collected)
    build_files = sorted(
        list((panel_factory_dir / "src" / "features").rglob("build_*.py"))
        + list((panel_factory_dir / "src" / "panels").rglob("build_*.py"))
    )
    if not build_files:
        raise DependencyError("No build_*.py files were found under panel_factory/src/.")

    specs: list[PipelineSpec] = []
    for path in build_files:
        spec = _extract_spec(path, panel_factory_dir, collected)
        if spec is None:
            continue
        _validate_spec(spec, path, panel_factory_dir, registry, collected)
        specs.append(spec)

    by_builder: dict[str, PipelineSpec] = {}
    for spec in specs:
        if spec.builder_name in by_builder:
            _warning(
                collected,
                spec.source,
                f"duplicate builder_name {spec.builder_name!r} (already declared by {by_builder[spec.builder_name].source}).",
            )
        else:
            by_builder[spec.builder_name] = spec
    known_builders = set(by_builder)
    for spec in specs:
        for dependency in spec.depends_on_builders:
            if dependency not in known_builders:
                _warning(collected, spec.source, f"depends_on_builders contains unknown builder {dependency!r}.")

    outputs: dict[str, str] = {}
    for spec in specs:
        for key in (*spec.writes_features, *spec.writes_panels):
            if key in outputs and outputs[key] != spec.builder_name:
                _warning(collected, spec.source, f"output key {key!r} is also written by {outputs[key]!r}.")
            outputs[key] = spec.builder_name
    return specs


def discover_artifacts(
    panel_factory_dir: Path,
    warnings: list[str] | None = None,
) -> list[PipelineSpec]:
    """Backward-compatible alias for callers of the pre-MVP generator."""

    return discover_specs(panel_factory_dir, warnings)


def resolve_graph(
    specs: list[PipelineSpec],
) -> tuple[list[PipelineSpec], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    by_name = {spec.builder_name: spec for spec in specs}
    dependencies = {
        spec.builder_name: tuple(
            dependency
            for dependency in spec.depends_on_builders
            if dependency in by_name
        )
        for spec in specs
    }
    downstream: dict[str, list[str]] = {name: [] for name in by_name}
    indegree = {name: len(values) for name, values in dependencies.items()}
    for child, parents in dependencies.items():
        for parent in parents:
            downstream[parent].append(child)
    ready = sorted(name for name, count in indegree.items() if count == 0)
    ordered_names: list[str] = []
    while ready:
        name = ready.pop(0)
        ordered_names.append(name)
        for child in sorted(downstream[name]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered_names) != len(specs):
        cycle = sorted(name for name, count in indegree.items() if count > 0)
        raise DependencyError("Builder dependency cycle detected: " + ", ".join(cycle))
    frozen_downstream = {name: tuple(sorted(values)) for name, values in downstream.items()}
    frozen_dependencies = {name: tuple(values) for name, values in dependencies.items()}
    return [by_name[name] for name in ordered_names], frozen_dependencies, frozen_downstream


def _code_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def _typed_reads(spec: PipelineSpec) -> str:
    parts = []
    for label, values in (
        ("raw", spec.reads_raw),
        ("feature", spec.reads_features),
        ("panel", spec.reads_panels),
    ):
        if values:
            parts.append(f"{label}: {_code_list(values)}")
    return "; ".join(parts) if parts else "none"


def _typed_writes(spec: PipelineSpec) -> str:
    parts = []
    for label, values in (("feature", spec.writes_features), ("panel", spec.writes_panels)):
        if values:
            parts.append(f"{label}: {_code_list(values)}")
    return "; ".join(parts) if parts else "none"


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_document(specs: list[PipelineSpec]) -> str:
    ordered, _, downstream = resolve_graph(specs)
    lines = [
        "<!-- Auto-generated by scripts/update_dependency_docs.py. Do not edit by hand. -->",
        "# Panel Factory Dependency Table",
        "",
        "This table is generated from top-level `PIPELINE_SPEC` dictionaries in `panel_factory/src/**/build_*.py`.",
        "Update a builder metadata block first, then run `python3 scripts/update_dependency_docs.py write`.",
        "",
        "## Builder Matrix",
        "",
        "| builder | stage | grain | reads | writes | keys | upstream |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec in ordered:
        row = [
            f"`{spec.builder_name}`",
            f"`{spec.stage}`",
            f"`{spec.grain}`",
            _typed_reads(spec),
            _typed_writes(spec),
            _code_list(spec.merge_keys),
            _code_list(spec.depends_on_builders),
        ]
        lines.append("| " + " | ".join(_table_cell(value) for value in row) + " |")

    lines.extend(["", "## Builder Cards", ""])
    for spec in ordered:
        lines.extend(
            [
                f"### `{spec.builder_name}`",
                f"- stage: `{spec.stage}`",
                f"- grain: `{spec.grain}`",
                f"- summary: {spec.summary}",
                f"- raw inputs: {_code_list(spec.reads_raw)}",
                f"- feature inputs: {_code_list(spec.reads_features)}",
                f"- panel inputs: {_code_list(spec.reads_panels)}",
                f"- outputs: {_typed_writes(spec)}",
                f"- merge keys: {_code_list(spec.merge_keys)}",
                f"- upstream builders: {_code_list(spec.depends_on_builders)}",
            ]
        )
        if spec.notes:
            lines.append(f"- notes: {'; '.join(spec.notes)}")
        if spec.contracts:
            lines.append(f"- contracts: {'; '.join(spec.contracts)}")
        if spec.downstream_consumers:
            lines.append(f"- downstream consumers: {_code_list(spec.downstream_consumers)}")
        lines.append(f"- downstream builders: {_code_list(downstream[spec.builder_name])}")
        lines.append(f"- builder file: `{spec.source}`")
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
        description="Validate PIPELINE_SPEC metadata and check or write the dependency map."
    )
    parser.add_argument("command", nargs="?", choices=("check", "write"), default="write")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    warnings: list[str] = []
    try:
        specs = discover_specs(PANEL_FACTORY_DIR, warnings)
        for message in warnings:
            print(message, file=sys.stderr)
        if warnings:
            print(
                f"Metadata validation found {len(warnings)} warning(s); fix them before regenerating the table.",
                file=sys.stderr,
            )
            return 1
        content = render_document(specs)
        current = OUTPUT_DOC.read_text(encoding="utf-8") if OUTPUT_DOC.exists() else None
        if args.command == "check":
            if current != content:
                print(
                    "Dependency table is stale. Run: python3 scripts/update_dependency_docs.py write",
                    file=sys.stderr,
                )
                return 1
            print(f"Dependency table is current: {OUTPUT_DOC.relative_to(REPO_ROOT)}")
            return 0
        if current == content:
            print(f"Dependency table already current: {OUTPUT_DOC.relative_to(REPO_ROOT)}")
            return 0
        atomic_write(OUTPUT_DOC, content)
        print(
            f"Generated {OUTPUT_DOC.relative_to(REPO_ROOT)} from {len(specs)} builder metadata block(s)."
        )
        return 0
    except (DependencyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
