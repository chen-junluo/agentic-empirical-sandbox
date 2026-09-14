# Artifact:    intermediate/question_intermediate
# Grain:       question
# Merge Keys:  question_id
#
# Inputs:
#   - data/raw/questions.csv  # example raw question source
#
# Output:      data/features/question_intermediate.csv
#   - Index: question_id
#   - Core: source_value
#   - Derived: none
#
# Logic:
#   - Read the raw question source without modifying it.
#   - Produce a minimal reusable question-level base table.

PIPELINE_SPEC = {
    "artifact": "intermediate/question_intermediate",
    "kind": "intermediate",
    "grain": "question",
    "merge_keys": ["question_id"],
    "inputs": ["data/raw/questions.csv"],
    "output": "data/features/question_intermediate.csv",
    "notes": "Replace the placeholder logic while preserving this artifact contract.",
}
