"""Canonical artifact-key registries used by pipeline metadata.

Builder metadata refers to these keys rather than repeating CSV filenames.
Keep the values literal and import-free so the dependency generator can inspect
this module with ``ast``.
"""

RAW_FILES = {
    "questions": {
        "path": "data/raw/questions.csv",
        "notes": "Example raw question source; raw data remains read-only.",
    },
}

FEATURE_OUTPUTS = {
    "question_intermediate": {
        "path": "data/features/question_intermediate.csv",
        "grain": "question",
        "keys": ["question_id"],
        "built_by": "build_example_intermediate",
        "kind": "intermediate",
    },
    "question_example_feature": {
        "path": "data/features/question_example_feature.csv",
        "grain": "question",
        "keys": ["question_id"],
        "built_by": "build_example_feature",
        "kind": "feature",
    },
}

PANEL_OUTPUTS = {
    "question_example_panel": {
        "path": "data/panels/question_example_panel.csv",
        "grain": "question",
        "keys": ["question_id"],
        "built_by": "build_example_panel",
        "kind": "panel",
    },
}

# Backward-compatible grouped view for callers that used the original registry.
ARTIFACT_PATHS = {
    "raw": RAW_FILES,
    "intermediate": {
        "question_intermediate": FEATURE_OUTPUTS["question_intermediate"],
    },
    "features": {
        "question_example_feature": FEATURE_OUTPUTS["question_example_feature"],
    },
    "panels": PANEL_OUTPUTS,
}
