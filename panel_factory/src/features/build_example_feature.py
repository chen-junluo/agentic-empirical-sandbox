# Artifact:    feature/question_example_feature
# Grain:       question
# Merge Keys:  question_id
#
# Inputs:
#   - question_intermediate  # data/features/question_intermediate.csv
#
# Output:      data/features/question_example_feature.csv
#   - Index: question_id
#   - Core: none
#   - Derived: example_feature
#
# Logic:
#   - Read the reusable question-level intermediate.
#   - Build one example question-level feature without mutating the intermediate.

PIPELINE_SPEC = {
    "artifact": "feature/question_example_feature",
    "kind": "feature",
    "grain": "question",
    "merge_keys": ["question_id"],
    "inputs": ["question_intermediate"],
    "output": "data/features/question_example_feature.csv",
    "notes": "Replace the placeholder logic while preserving this artifact contract.",
}
