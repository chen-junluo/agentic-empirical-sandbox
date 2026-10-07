# `panel_factory/src/` rules

- `src/features/` 和 `src/panels/` 下的每个 `build_*.py` 都必须保留顶部 bullet 注释。
- 顶部注释下方必须紧跟一个顶层常量 `PIPELINE_SPEC`；不要用 decorator、YAML frontmatter 或运行时生成 metadata。
- `PIPELINE_SPEC` 必须声明：
  - `builder_name`、`stage`、`grain`、一句话 `summary`
  - `reads_raw`、`reads_features`、`reads_panels`
  - `writes_features`、`writes_panels`
  - `merge_keys`、`depends_on_builders`
  - 可选的 `notes`、`contracts`、`downstream_consumers`
- `reads_*` / `writes_*` 使用 `src/utils/paths.py` 中的 canonical artifact key，不直接重复 CSV 文件名。
- `stage` 只能是 `feature`、`intermediate`、`panel`，并且必须和 builder 所在目录及输出 registry 一致。
- `merge_keys` 必须反映代码真实使用的主要 join keys；`depends_on_builders` 只写直接逻辑上游。
- 顶部注释负责变量定义、构造步骤和操作性定义；`PIPELINE_SPEC` 只负责结构化依赖信息。
- 修改 builder 或 `PIPELINE_SPEC` 后，必须从 repository root 运行：
  - `python3 scripts/update_dependency_docs.py check`
  - 确认无 warning 后运行 `python3 scripts/update_dependency_docs.py write`
