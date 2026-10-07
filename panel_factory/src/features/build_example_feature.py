# - Builds one compact question-level feature.
#   - Reads the reusable question-level intermediate.
#   - Builds one example feature without mutating the intermediate.
#   - Writes a feature table keyed by question_id for late merge.

PIPELINE_SPEC = {
    "builder_name": "build_example_feature",
    "stage": "feature",
    "grain": "question",
    "summary": "Build one compact question-level feature from the reusable intermediate.",
    "reads_raw": [],
    "reads_features": ["question_intermediate"],
    "reads_panels": [],
    "writes_features": ["question_example_feature"],
    "writes_panels": [],
    "merge_keys": ["question_id"],
    "depends_on_builders": ["build_example_intermediate"],
    "notes": ["Replace the placeholder logic while preserving this artifact contract."],
    "contracts": ["one row per question_id"],
    "downstream_consumers": ["build_example_panel"],
}
