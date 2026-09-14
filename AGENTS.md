# AGENTS.md

- 这是一个科研项目 workspace，不是单一项目仓库。当前 workspace 主要包含三类内容：
  - `archive/`：legacy materials。这里放旧 analysis scripts、旧 panel、旧 tables / figures、旧 writeup。主要用于参考，不应默认视为当前主流程。
  - `panel_factory/`：shared data pipeline。用于从 raw data 生成 features，再将 features 合并为 panels。
  - `projects/`：downstream research spaces。项目分析、回归、写作等工作原则上应建立在 `panel_factory/` 产出的数据之上。

---
## 1. 项目文件夹和架构详细介绍

- `panel_factory/` 的核心概念
  - 主要逻辑是读取 raw data -> 生成 feature tables -> 将 feature tables 合并为最终 panels。
  - panel 的构建不是把所有逻辑都堆在一个大表上反复改。更合适的方式是：在某个 `intermediate` base table 上，late merge 多个 compact features，最后形成 panel。
  - 内部文件架构如下：
    - `data/raw/`：原始数据，只读
    - `data/features/`：生成的 feature 表，以及部分重要 intermediate
    - `data/panels/`：最终 panel 数据
    - `src/features/`：feature 生成脚本
    - `src/panels/`：panel 聚合脚本
    - `src/utils/`：shared utilities，例如 `paths`、registry、I/O helpers
    - `documents/`：可选参考文档。作用是减少重复阅读、节省 token、方便复查。这里不是必须层，也不是 canonical rule source；规则与协作方式以 `AGENTS.md` 为准。如果 `documents/` 与 `AGENTS.md` 不一致，应优先修正或忽略 `documents/`。如果某些内容需要修改或沉淀，不仅要更新对应 `documents/`，也要在合适层级的 `AGENTS.md` 中补充 reference，确保这些参考文档能被稳定引用。
    - `notebooks/`：用于 dashboard-style orchestration，供用户手动运行 pipeline，调用 `src/` 下的各类 Python scripts。不要默认把 notebooks 当作一次性实验文件，也不要在未经说明的情况下把 notebook workflow 改写成别的交互方式。
- `projects/`
  - 这里存放具体研究项目。每个 project folder 通常包括：项目说明、决策记录与待办、分阶段的 analysis、分阶段的 writeup。
  - 这些 project folders 是 `panel_factory/` 下游的研究工作区，不是 shared data pipeline 本身。因此：
    - 项目 analysis code 不要与通用 pipeline code 混淆
    - project-specific logic 不要随意上移到 `panel_factory/`
    - 写作材料、regression scripts、tables / figures，应优先放在各自 project 内部管理
  - `projects/` 层的 references 统一由 `projects/AGENTS.md` 建立；其中：
    - `projects/documents/project_workspace_structure.md` 承接 workspace structure 与 stage conventions
    - `projects/documents/analysis_script_template.md` 承接 analysis script template 与 coding rules
    - `projects/documents/analysis_output_rules.md` 承接 output conventions、result interpretation 与 failed-run handling
- `archive/`
  - 这里是迁移前的旧架构内容和历史项目材料。
  - 用途：回溯旧逻辑、查找历史 scripts 或 intermediate results、对照迁移前后的处理方式。
  - 默认规则：
    - `archive/` 不是当前主流程
    - 不要默认把 `archive/` 中的代码当作最新版本
    - 如需复用旧逻辑，应先与 `panel_factory/` 当前实现核对
  - 如任务涉及任何数字化转型、reconstruction、legacy workflow 拆解、迁移前逻辑梳理，立即参考 `archive/AGENTS.md`。

---
## 2. 默认工作边界

- 除非用户明确要求，否则不要自动进行以下操作：
  - 不要为了“更整洁”而重命名 folders
  - 不要自动重组 workspace structure
  - 不要随意改动 raw data
  - 不要轻易修改 feature names、column names、merge keys、output filenames
  - 不要把 `archive/` 误当作当前 production code
  - 不要把项目内部 analysis logic 直接混入 `panel_factory/`
  - 不要未经说明就重写 notebook-driven workflow

---
## 3. 任务定位规则

- 当用户提出任务时，先按下面的方式定位：
  - 如果任务涉及 raw data、feature generation、panel construction、pipeline utilities，优先查看 `panel_factory/`
  - 如果任务涉及 regression、empirical analysis、tables / figures、paper writing，优先查看 `projects/`
  - 如果任务涉及 historical versions、旧架构、迁移前逻辑，查看 `archive/`
  - 如果任务涉及数字化转型、reconstruction、legacy workflow 拆解，除查看 `archive/` 外，还要优先遵守 `archive/AGENTS.md`

---
## 4. 局部说明与协作方式

- 如果某个 subfolder 下还有自己的 `AGENTS.md`，在该目录范围内应同时遵守更局部的规则。
- 例如在 `panel_factory/` 内工作时，应同时遵守 `panel_factory/AGENTS.md`。
- 协作风格：
  - 中文简洁描述内容，technical terms 用 English
  - 当 structure 不清晰时，先列 inventory，再提 reconstruction plan
  - 优先尊重已有 artifact names、merge keys、output boundaries，再逐步优化
- 撰写或修改 instruction files 时：
  - 使用缩进组织的 nested bullet points，不写松散长段落
  - 标题克制，最多使用 `##` 二级标题
  - 每个 main section 前使用 `---`，主项保持数字序号
  - 代码相关内容，包括 `file paths`、`folder names`、`variable names`、`commands`、`config keys`，使用行内代码
  - 先给 structure，再给 explanation；优先用 bullet hierarchy 表达 `scope`、`priority`、`rules`、`exceptions`

---
## 5. Upstream 更新与 user-specific boundary

- 手动检查和同步 public template：
  - `python3 scripts/update_template.py check`
  - `python3 scripts/update_template.py apply`
  - 完成后运行 `git diff`；updater 不会自动 commit
- 所有允许用户定制的 instruction files 都必须且只能包含一个 `## User-Specific Rules` marker：
  - marker 之前是 upstream-managed public rules
  - marker 本身及其后全部内容是 user-specific content
  - shared、tool-neutral 的自定义规则放在 `AGENTS.md` marker 后
  - Claude Code-specific additions 放在对应 `CLAUDE.md` marker 后
- updater 只处理 `scripts/template_manifest.json` 明确列出的 paths，不通过 recursive scan 扩大 managed scope。
- 未列入 manifest 的文件、实际研究数据、archive materials 和用户创建的 project content 默认受保护。

---
## User-Specific Rules

<!-- 在此添加 tool-neutral、workspace-specific rules -->
