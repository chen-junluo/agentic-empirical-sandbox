# Project workspace structure and stage conventions

---
## 1. Scope
- 适用范围
  - 本文档用于 `projects/` 下 project workspace 的默认目录结构与 stage conventions。
  - 目标是减少在 `projects/AGENTS.md` 中重复展开 folder-level 说明。
- precedence
  - 如某个具体 project 或 stage 下存在更局部的 `AGENTS.md`，以更局部规则为准。
  - 如用户在当前任务中给出明确结构要求，以用户要求为准。

---
## 2. Project-level structure
- `projects/` 用于承接 downstream research projects，不是 shared pipeline 本体。
- 一个 data source、feature set 或 panel 可能服务多个 projects，所以 `projects/` 与 `panel_factory/` 必须分离。
- 单个 project 的默认最小结构：
  - `dashboard/`
    - 记录 todo 与 decisions
  - 多个 stage 文件夹
    - 每个 stage 与 `dashboard/` 平行，例如 `202405 ICIS/`、`202501 MISQ/`
  - 如需其他 project-specific materials，应放在 project 内部，不要上移到共享 pipeline

---
## 3. Stage-level structure
- 每个 stage 文件夹默认包含：
  - `analysis/`
    - active empirical analysis
    - `R/`、`Stata/` 放 analysis scripts
    - outputs 默认写到 sibling `outputs/`
    - 如有定稿整理，可放到 `finalize/`
  - `writeup/`
    - 当前 stage 的 manuscript draft 放在这里
    - `submitted version/` 用于该 stage 的投稿版本归档
- 目标
  - analysis、writeup、submission archive 分层清楚
  - 当前活跃工作与已提交版本分离
  - 便于 AI 修改、用户分块执行、结果回读

---
## 4. Usage notes
- 若任务涉及 analysis script 的写法、输出规则、regression coding conventions，参考 `projects/documents/analysis_script_template.md`
- 若只是判断某个文件该放哪一层、某个 stage 应如何组织，优先参考本文档
