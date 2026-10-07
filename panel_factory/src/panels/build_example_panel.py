# - Assembles the final question-level panel.
#   - Reads the reusable intermediate and compact feature.
#   - Late-merges them on question_id without rebuilding upstream artifacts.

PIPELINE_SPEC = {
    "builder_name": "build_example_panel",
    "stage": "panel",
    "grain": "question",
    "summary": "Assemble the final question-level panel by late-merging the intermediate and feature.",
    "reads_raw": [],
    "reads_features": ["question_intermediate", "question_example_feature"],
    "reads_panels": [],
    "writes_features": [],
    "writes_panels": ["question_example_panel"],
    "merge_keys": ["question_id"],
    "depends_on_builders": ["build_example_intermediate", "build_example_feature"],
    "notes": ["Replace the placeholder logic while preserving this artifact contract."],
    "contracts": ["late merge on question_id", "does not rebuild upstream artifacts"],
}
