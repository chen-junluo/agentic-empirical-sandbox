---
## Builder metadata template

- 所有 `src/features/build_*.py` 和 `src/panels/build_*.py` 必须在顶部 bullet 注释后紧跟顶层 `PIPELINE_SPEC`
- `PIPELINE_SPEC` 必须是普通 Python literal dict，方便 generator 用 `ast` 提取
- 输入输出使用 `src/utils/paths.py` 中的 canonical artifact key，不直接写 CSV 文件名

---
## 模板格式

```python
# - Builds one compact question-level feature.
#   - Reads the reusable intermediate and preserves question_id as the key.
#   - Writes a late-merge feature table.

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
    "notes": ["compact feature table"],
    "contracts": ["one row per question_id"],
    "downstream_consumers": ["build_example_panel"],
}
```

---
## 字段职责

- 顶部注释负责变量定义、构造步骤和操作性定义
- `PIPELINE_SPEC` 负责机器可读的 stage、grain、canonical inputs/outputs、keys 和直接上游
- `stage` 只能是 `feature`、`intermediate`、`panel`
- `summary` 保持一句话；`merge_keys` 写代码真实使用的主要 join keys

---
## 自动生成 dependency table

- 验证 metadata 并检查 table 是否为最新：`python3 scripts/update_dependency_docs.py check`
- 验证 metadata 并刷新 table：`python3 scripts/update_dependency_docs.py write`
- 不要手工编辑 `documents/pipeline_dependency_table.md`
