# - Builds the reusable question-level intermediate.
#   - Reads the example raw question source without modifying it.
#   - Produces a minimal reusable base table keyed by question_id.

PIPELINE_SPEC = {
    "builder_name": "build_example_intermediate",
    "stage": "intermediate",
    "grain": "question",
    "summary": "Build the reusable question-level intermediate from the raw question source.",
    "reads_raw": ["questions"],
    "reads_features": [],
    "reads_panels": [],
    "writes_features": ["question_intermediate"],
    "writes_panels": [],
    "merge_keys": ["question_id"],
    "depends_on_builders": [],
    "notes": ["Replace the placeholder logic while preserving this artifact contract."],
    "contracts": ["one row per question_id", "raw source is read-only"],
    "downstream_consumers": ["build_example_feature", "build_example_panel"],
}
