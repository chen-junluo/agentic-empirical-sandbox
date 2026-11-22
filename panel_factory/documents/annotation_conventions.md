---
## 1. Scope 与文件位置

- 参考文档，不是 rule source；冲突时以 `AGENTS.md` 为准
- annotation 临时文件放在 `data/TEMP/features/<feature_name>/`，用 `src/utils/cache_utils.py` 的 `annotation_temp_dir()` 取路径；`data/TEMP/` 已 gitignored
- 最终 feature 输出到 `data/features/<grain>_<feature_name>.csv`，并在 `src/utils/paths.py` 的 `FEATURE_OUTPUTS` 注册

---
## 2. Workflow 文件命名

- Candidate table：`<grain>_annotation_candidates.csv`
- Per-coder sheets：`<grain>_annotation_candidates_RA1.csv`、`<grain>_annotation_candidates_RA2.csv`
- Finalized annotations：`<grain>_annotation_candidates_done.csv`
- Coding manual：`<coder_role>_coding_manual.md`

---
## 3. Script 分工

- Candidate preparer：`src/features/prepare_<grain>_<feature_name>_candidates.py`
  - 生成 candidate table 和 coding manual，只写入 TEMP 目录
  - 使用 `prepare_*` 前缀而非 `build_*`：它不产出 registry artifact，不进入 `update_dependency_docs.py` 的 dependency scan，不需要 `PIPELINE_SPEC`
- Feature builder：`src/features/build_<grain>_<feature_name>.py`
  - 读取 `_done.csv`，验证完整性，生成最终 feature
  - 遵守 `src/AGENTS.md` 的 `PIPELINE_SPEC` 规则
- LLM annotation：不在代码中实现 finalize、prepare、summarize 流程；由 AI agent 读取 RA1/RA2 后生成 `_done.csv`，feature builder 只负责验证和转换

---
## 4. Validation 要求

- Feature builder 必须验证所有样本都有完整标注，缺失时报错而不是静默填充
- 必须验证 merge keys 与 candidate table 一致，没有重复或丢失
- 必须报告 inter-rater reliability，例如 Cohen's kappa
