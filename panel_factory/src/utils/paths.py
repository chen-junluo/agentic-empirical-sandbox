"""Canonical artifact path registry placeholder.

Use this file to register stable artifact contracts for `intermediate`,
`feature`, and `panel` outputs. Keep it lightweight but explicit so later
pipeline scripts and AI collaborators can reuse the same names and paths.
"""

ARTIFACT_PATHS = {
    "intermediate": {
        "question_intermediate": {
            "path": "data/features/question_intermediate.csv",
            "grain": "question",
            "keys": ["question_id"],
            "built_by": "src/panels/build_example_intermediate.py",
            "notes": "Replace with actual intermediate artifact contract.",
        },
    },
    "features": {
        "question_example_feature": {
            "path": "data/features/question_example_feature.csv",
            "grain": "question",
            "keys": ["question_id"],
            "built_by": "src/features/build_example_feature.py",
            "notes": "Replace with actual feature artifact contract.",
        },
    },
    "panels": {
        "question_example_panel": {
            "path": "data/panels/question_example_panel.csv",
            "grain": "question",
            "keys": ["question_id"],
            "built_by": "src/panels/build_example_panel.py",
            "notes": "Replace with actual panel artifact contract.",
        },
    },
}
