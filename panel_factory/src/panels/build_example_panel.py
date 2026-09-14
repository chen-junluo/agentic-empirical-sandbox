# Artifact:    panel/question_example_panel
# Grain:       question
# Merge Keys:  question_id
#
# Inputs:
#   - question_intermediate  # data/features/question_intermediate.csv
#   - question_example_feature  # data/features/question_example_feature.csv
#
# Output:      data/panels/question_example_panel.csv
#   - Index: question_id
#   - Core: source_value
#   - Derived: example_feature
#
# Logic:
#   - Read the reusable question-level intermediate and compact feature.
#   - Late merge on question_id without rebuilding either upstream artifact.

PIPELINE_SPEC = {
    "artifact": "panel/question_example_panel",
    "kind": "panel",
    "grain": "question",
    "merge_keys": ["question_id"],
    "inputs": ["question_intermediate", "question_example_feature"],
    "output": "data/panels/question_example_panel.csv",
    "notes": "Replace the placeholder logic while preserving this artifact contract.",
}
