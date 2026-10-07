# AGENTS.md

- `panel_factory/` 是 shared data pipeline，不是 project-specific analysis space
- 核心职责：从 raw 中稳定地重建 reusable intermediate、features、final panels
- 代码来源听从用户指示，可以用 `archive/` 重建，也可以根据 natural-language instructions

---
## 1. Working rules

- Prioritize consistency with the current notebook pipeline before improving logic
- Treat existing intermediate artifact names as contracts during the first migration pass
- Preserve write/read CSV boundaries when they affect downstream behavior
- Do not rename columns, merge keys, or staged output files unless all downstream consumers are updated together
- Keep raw data read-only
- 不要重复实现前序步骤已经完成的处理逻辑
  - 如果当前 variable 的生成依赖 raw-like source、某些 intermediate 或 feature，而这些 artifacts 已经可以由 `src/` 下现有 scripts 生成，则默认优先复用已有产物
  - 当前 script 应直接使用这些已有的 intermediate 或 feature 作为 input，不要重复生成相同产物
- 每次交付时：
  - 默认要求每个 code file 内部是完整、`self-consistent` 的
  - 不要出现 comments、实际 logic、naming meaning 彼此不一致的情况
- 对代码注释的处理：
  - 不要删除中英夹杂的现有 comments
  - 这类 comments 通常包含 `context`、research process 信息或 `domain knowledge`
  - 如果代码改动改变了这些 comments 的含义，应更新内容，而不是直接删掉
- 重视 canonical source clarity
  - 优先复用 upstream 已有 variables，避免重复 alias，避免 downstream 误读和 missing-value contamination

---
## 2. 核心概念与架构

- 主要逻辑：`raw data` → `feature tables` → `final panels`
  - panel 的构建不要在一个 full panel 上一路追加很多 variables，再输出更大的 intermediate
  - 优先保持 `intermediate`、`features`、`panel` 三层解耦
  - panel builder 的职责应尽量收敛到：读取 intermediate、merge features、写出 panel
- **Grain vs Intermediate 的区别**
  - **Grain**：从 analysis level 判断它属于哪个 level 的 panel
    - 四个核心 grain：`question`、`human_answer`、`full_answer`、`user_activity`
    - Grain 决定 merge keys 和 data granularity
    - 例如：`human_answer` grain 的 merge keys 是 `questionURL × resp_id`
  - **Intermediate**：从 data generation 角度判断；如果后续会被不断复用，它就是 Intermediate
    - Intermediate 是 base table，minimal processing
    - Feature 是 compact table，specific metrics
    - Panel 是 final table，late merge features onto intermediate
  - **命名规范**
    - Feature filename 必须以 grain 开头：`{grain}_{feature_name}.csv`
    - Intermediate filename 必须包含 `_intermediate` suffix：`{grain}_intermediate.csv`
- 内部文件架构：
  - `data/raw/`：原始数据，只读
  - `data/features/`：生成的 feature tables，以及部分重要 intermediate
  - `data/panels/`：final panel data
  - `src/features/`：生成 compact feature tables
  - `src/panels/`：把 features late merge 到某个 intermediate 上，生成 final panel
  - `src/utils/`：shared utilities，例如 `paths`、registry、I/O helpers
  - `documents/`：可选 reference documents
    - 作用：减少重复阅读、节省 token、方便复查
    - 不是必须层，也不是 canonical rule source
    - 规则与协作方式以 `AGENTS.md` 为准
    - 如果 `documents/` 与 `AGENTS.md` 不一致，应优先修正或忽略 `documents/`
    - 当前默认参考：`documents/features_registry.md`、`documents/pipeline_dependency_table.md`
    - 如需修改或沉淀，不仅要更新对应 `documents/`，也要在合适层级的 `AGENTS.md` 中补充 reference
  - `notebooks/`：dashboard-style orchestration，供用户手动运行 pipeline，调用 `src/` 下的各类 Python scripts
    - 不要默认把 notebooks 当作一次性 experiment files
    - 不要在未经说明的情况下把 notebook workflow 改写成别的 interaction pattern

---
## 3. 写新代码时的默认判断

- 如果要加的是 reusable variable，先判断它是否应该成为一个独立 feature table
- 如果某段 logic 只是某个 project 的临时 analysis requirement，不要直接写进 `panel_factory/`
- 如果当前目标只是 assemble 一个 panel，不要顺手把 feature generation 也塞进 panel builder
- 如果已有 intermediate 或 feature 已能支持当前任务，直接复用，不要重复造轮子
- 涉及 artifact dependencies 时，优先参考 `documents/pipeline_dependency_table.md`
- 涉及 `feature` 是否已存在、是否应复用时，优先参考 `documents/features_registry.md`
- 对于非 feature generation 的简单查询检索任务，直接后台分析并告诉用户结果。**如无要求，不要在本地写入 `.py` file 和 report。**

---
## 4. `build_*.py` metadata 与 pipeline consistency

- 当新建或修改任何 `build_*.py` 时，至少必须同步完成两步：
  1. 保留顶部 bullet 注释，并修改紧随其后的 `PIPELINE_SPEC`，确保与 actual code logic 一致
  2. 运行 `python3 scripts/update_dependency_docs.py write`，由 metadata 重新生成 `documents/pipeline_dependency_table.md`
- 不要手工维护 generated dependency table；使用 `python3 scripts/update_dependency_docs.py check` 检查 metadata warning 和 table 是否过期
- 如果改动改变某个 `feature` contract，例如 `grain`、`merge_keys`、`output_path` 或 reusable meaning：
  - 还应同步更新 `documents/features_registry.md`
- `PIPELINE_SPEC` 强制要求：
  - 所有 `build_*.py` 必须包含顶部的普通 Python dict
  - 必填字段和 canonical artifact keys 必须严格遵守 `documents/build_file_header_template.md` 与 `src/AGENTS.md`
  - `stage` 必须和 builder 目录及输出 registry 一致
  - `merge_keys` 必须反映代码真实使用的主要 join keys，`depends_on_builders` 只写直接上游

---
## 5. 每次生成新 feature 后的默认反馈

- 至少包括 `min`、`max`、`mean`
- 大概说明 variable distribution 的数值范围
- 默认补充若干 sample rows，优先查看命中值为 `1` 的 cases
- 如果 sample 过长，只简要保留关键点，不要直接输出全部内容
- 不需要把 descriptive statistics 和 samples 存成 CSV，直接在对话中反馈

---
## 6. 运行 Python scripts

- 不要直接从 script file path 裸调用 Python，否则可能出现 `ModuleNotFoundError`
- 默认使用 notebook 对应的 interpreter，并从 workspace root 设置动态 `PYTHONPATH`
- 例如：

  ```bash
  PYTHONPATH="$(pwd)/panel_factory/src" python3 panel_factory/src/panels/build_xxxxx_panel.py
  ```

---
## User-Specific Rules

<!-- 在此添加 panel_factory 特定规则 -->
