---
## 标准 Header Template

- 所有 `src/features/build_*.py` 和 `src/panels/build_*.py` 必须使用此模板
- 放在文件最顶部，作为 structured comment header
- 严格遵守格式，确保可自动化解析
- 所有示例字段都是 required；`none` 表示该类 output columns 为空

---
## 模板格式

```python
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
#   - Build one compact feature without mutating the intermediate.
```

---
## 字段说明

- **Artifact**: `{intermediate|feature|panel}/{artifact_key}` 格式；`artifact_key` 必须与 output filename stem 相同
- **Grain**: 默认使用 `question`、`human_answer`、`full_answer`、`user_activity` 四个 core grains
- **Merge Keys**: 该 artifact 的 index columns，用于 merge 操作
- **Inputs**: 每行第一个 token 写 upstream `artifact_key` 或 external source path；可在后面的 `#` comment 中补充 path 或说明
- **Output**: 输出文件路径，紧接着列出输出列结构
  - **Index**: index columns
  - **Core**: 核心业务字段
  - **Derived**: 派生计算字段
- **Logic**: 关键处理逻辑，用 bullet points 简要描述

---
## 格式规则

- 使用纯 `#` 注释，不使用装饰性字符（`═`、`─`、`║` 等）
- 用缩进表达层级关系（2 空格）
- section 之间用一个空 `#` 行分隔
- `feature` output 必须命名为 `{grain}_{feature_name}.csv`
- `intermediate` output 必须命名为 `{grain}_intermediate.csv`
- `panel` output 必须以 `{grain}_` 开头并使用 `.csv`

---
## 自动生成 dependency map

- 验证 headers 并检查 map 是否为最新：`python3 scripts/update_dependency_docs.py check`
- 验证 headers 并刷新 map：`python3 scripts/update_dependency_docs.py write`
- 任一 header 缺字段、artifact/output 重复、命名不合规或依赖成环时，generator 会停止且不覆盖现有 map
