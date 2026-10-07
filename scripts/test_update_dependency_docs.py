#!/usr/bin/env python3
"""Tests for the PIPELINE_SPEC dependency metadata generator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from update_dependency_docs import DependencyError, discover_specs, render_document


REGISTRY = '''
RAW_FILES = {"questions": {"path": "data/raw/questions.csv"}}
FEATURE_OUTPUTS = {
    "question_intermediate": {"path": "data/features/question_intermediate.csv"},
    "question_example_feature": {"path": "data/features/question_example_feature.csv"},
}
PANEL_OUTPUTS = {"question_example_panel": {"path": "data/panels/question_example_panel.csv"}}
'''


def spec(
    builder: str,
    stage: str,
    reads_raw: list[str] | None = None,
    reads_features: list[str] | None = None,
    writes_features: list[str] | None = None,
    writes_panels: list[str] | None = None,
    depends: list[str] | None = None,
) -> str:
    return f'''# - Test builder metadata.

PIPELINE_SPEC = {{
    "builder_name": "{builder}",
    "stage": "{stage}",
    "grain": "question",
    "summary": "Build the {builder} artifact.",
    "reads_raw": {reads_raw or []!r},
    "reads_features": {reads_features or []!r},
    "reads_panels": [],
    "writes_features": {writes_features or []!r},
    "writes_panels": {writes_panels or []!r},
    "merge_keys": ["question_id"],
    "depends_on_builders": {depends or []!r},
}}
'''


class DependencyMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="dependency-map-test-")
        self.root = Path(self.temporary.name) / "panel_factory"
        (self.root / "src" / "features").mkdir(parents=True)
        (self.root / "src" / "panels").mkdir(parents=True)
        paths = self.root / "src" / "utils" / "paths.py"
        paths.parent.mkdir(parents=True)
        paths.write_text(REGISTRY, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_renders_builder_matrix_and_cards(self) -> None:
        self.write(
            "src/panels/build_base.py",
            spec(
                "build_base",
                "intermediate",
                reads_raw=["questions"],
                writes_features=["question_intermediate"],
            ),
        )
        self.write(
            "src/features/build_feature.py",
            spec(
                "build_feature",
                "feature",
                reads_features=["question_intermediate"],
                writes_features=["question_example_feature"],
                depends=["build_base"],
            ),
        )

        warnings: list[str] = []
        document = render_document(discover_specs(self.root, warnings))

        self.assertEqual([], warnings)
        self.assertIn("## Builder Matrix", document)
        self.assertIn("## Builder Cards", document)
        self.assertIn("build_base", document)
        self.assertIn("build_feature", document)
        self.assertIn("raw: `questions`", document)

    def test_missing_spec_is_reported_as_warning(self) -> None:
        self.write("src/features/build_broken.py", "x = 1\n")
        warnings: list[str] = []

        specs = discover_specs(self.root, warnings)

        self.assertEqual([], specs)
        self.assertTrue(any("PIPELINE_SPEC" in warning for warning in warnings))

    def test_unknown_registry_key_is_reported_as_warning(self) -> None:
        self.write(
            "src/features/build_feature.py",
            spec(
                "build_feature",
                "feature",
                reads_features=["missing_feature"],
                writes_features=["question_example_feature"],
            ),
        )
        warnings: list[str] = []

        discover_specs(self.root, warnings)

        self.assertTrue(any("unknown canonical artifact key" in warning for warning in warnings))

    def test_invalid_stage_is_reported_as_warning(self) -> None:
        self.write(
            "src/features/build_feature.py",
            spec("build_feature", "analysis", writes_features=["question_example_feature"]),
        )
        warnings: list[str] = []

        discover_specs(self.root, warnings)

        self.assertTrue(any("stage 'analysis' is invalid" in warning for warning in warnings))

    def test_dependency_cycle_is_rejected(self) -> None:
        self.write(
            "src/features/build_a.py",
            spec("build_a", "feature", writes_features=["question_example_feature"], depends=["build_b"]),
        )
        self.write(
            "src/panels/build_b.py",
            spec("build_b", "intermediate", writes_features=["question_intermediate"], depends=["build_a"]),
        )

        warnings: list[str] = []
        specs = discover_specs(self.root, warnings)

        with self.assertRaisesRegex(DependencyError, "cycle"):
            render_document(specs)

    def test_builder_imports_are_never_executed(self) -> None:
        self.write(
            "src/features/build_feature.py",
            "raise RuntimeError('must not execute')\n" + spec(
                "build_feature", "feature", writes_features=["question_example_feature"]
            ),
        )

        warnings: list[str] = []
        specs = discover_specs(self.root, warnings)

        self.assertEqual([], warnings)
        self.assertEqual("build_feature", specs[0].builder_name)


if __name__ == "__main__":
    unittest.main()
