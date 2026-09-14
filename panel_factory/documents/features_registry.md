---
## 1. feature registry
- 作用
  - 记录 `feature` artifacts 的最小注册信息，减少重复阅读与重复造轮子。
  - 这是参考文档，不是 rule source；规则仍以 `AGENTS.md` 为准。
- 使用规则
  - 新增或重构 `feature` 时，优先检查这里是否已有可复用条目。
  - 如果 `feature` contract 发生变化，应同步更新本文件与相关 `AGENTS.md` reference。

---
## 2. registry table
| feature_name | grain | merge_keys | built_by | output_path | notes |
| --- | --- | --- | --- | --- | --- |
| `question_example_feature` | `question` | `question_id` | `build_example_feature.py` | `data/features/question_example_feature.csv` | example contract; replace its placeholder logic for a real project |
