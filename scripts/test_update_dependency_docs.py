#!/usr/bin/env python3
"""Tests for the generated panel-factory dependency map."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from update_dependency_docs import DependencyError, discover_artifacts, render_document


def header(
    kind: str,
    key: str,
    grain: str,
    inputs: list[str],
    output: str,
) -> str:
    input_lines = "\n".join(f"#   - {value}" for value in inputs)
    return f"""# Artifact:    {kind}/{key}
# Grain:       {grain}
# Merge Keys:  question_id
#
# Inputs:
{input_lines}
#
# Output:      {output}
#   - Index: question_id
#   - Core: source_value
#   - Derived: example_value
#
# Logic:
#   - Test the declared dependency.

PIPELINE_SPEC = {{}}
"""


class DependencyMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="dependency-map-test-")
        self.root = Path(self.temporary.name) / "panel_factory"
        (self.root / "src" / "features").mkdir(parents=True)
        (self.root / "src" / "panels").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_renders_dependency_graph_and_contracts(self) -> None:
        self.write(
            "src/panels/build_base.py",
            header(
                "intermediate",
                "question_intermediate",
                "question",
                ["data/raw/questions.csv"],
                "data/features/question_intermediate.csv",
            ),
        )
        self.write(
            "src/features/build_feature.py",
            header(
                "feature",
                "question_example_feature",
                "question",
                ["question_intermediate"],
                "data/features/question_example_feature.csv",
            ),
        )

        document = render_document(discover_artifacts(self.root))

        self.assertIn("flowchart LR", document)
        self.assertIn("question_intermediate", document)
        self.assertIn("question_example_feature", document)
        self.assertIn("data/raw/questions.csv", document)
        self.assertIn("## Artifact contracts", document)

    def test_missing_header_field_is_rejected(self) -> None:
        self.write("src/features/build_broken.py", "PIPELINE_SPEC = {}\n")

        with self.assertRaisesRegex(DependencyError, "Artifact"):
            discover_artifacts(self.root)

    def test_feature_name_must_begin_with_grain(self) -> None:
        self.write(
            "src/features/build_bad_name.py",
            header(
                "feature",
                "example_feature",
                "question",
                ["data/raw/questions.csv"],
                "data/features/example_feature.csv",
            ),
        )

        with self.assertRaisesRegex(DependencyError, "feature output"):
            discover_artifacts(self.root)

    def test_dependency_cycle_is_rejected(self) -> None:
        self.write(
            "src/panels/build_base.py",
            header(
                "intermediate",
                "question_intermediate",
                "question",
                ["question_example_feature"],
                "data/features/question_intermediate.csv",
            ),
        )
        self.write(
            "src/features/build_feature.py",
            header(
                "feature",
                "question_example_feature",
                "question",
                ["question_intermediate"],
                "data/features/question_example_feature.csv",
            ),
        )

        with self.assertRaisesRegex(DependencyError, "cycle"):
            render_document(discover_artifacts(self.root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
