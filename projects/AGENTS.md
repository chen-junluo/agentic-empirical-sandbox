# AGENTS.md

- `projects/` 用于承接 downstream research projects，不是 shared pipeline 本体
- 一个 data source、feature set 或 panel 可能服务多个 projects，所以 `projects/` 与 `panel_factory/` 必须分离
- 本文件只保留 `projects/` 层的 collaboration boundaries、task routing 与 document references

---
## 1. Reference map

- project workspace 的默认 directory structure 与 stage conventions → `projects/documents/project_workspace_structure.md`
- analysis script 的默认 code template 与 coding rules → `projects/documents/analysis_script_template.md`
- analysis output conventions、result interpretation、failed-run handling 与 exploratory regression workflow → `projects/documents/analysis_output_rules.md`
- 如后续需要沉淀新的 reusable rule，优先新增或更新 `projects/documents/*.md`，再由本文件建立 stable reference

---
## 2. Core boundaries

- `projects/` 用于承接 downstream research projects，不是 shared pipeline 本体
- 项目 analysis code 不要与通用 pipeline code 混淆
- project-specific logic 不要随意上移到 `panel_factory/`
- writing materials、regression scripts、tables / figures，应优先放在各自 project 内部管理
- 如任务涉及 folder placement、stage layout、analysis/writeup/submission archive 的组织，参考 `projects/documents/project_workspace_structure.md`

---
## 3. Default workflow

- agent 在 `projects/` 下处理 analysis task 时，默认按下面方式工作：
  - 读取现有 analysis script
  - 在现有 file 基础上修改，或按需要新建 AI-friendly `.R` analysis script
    - 具体 script template 与 coding rules → `projects/documents/analysis_script_template.md`
    - 具体 output rules 与 regression workflow → `projects/documents/analysis_output_rules.md`
  - 运行对应 analysis
  - 读取保存到 `outputs/` 的 results
  - 在对话框中用简洁中文总结 results
  - 根据用户后续指示继续迭代现有 file，或新建新的 analysis file
- 重点不是把代码写成 presentation-style document，而是让 analysis script：
  - agent 容易修改
  - 用户容易分块执行
  - output path 明确
  - results 容易回读

---
## 4. Cairnwork role routing

- project-level Cairnwork initialization → `${CAIRNWORK_ROOT}/agents/project_initializer.md`
- Node validation, execution, rerun, result protocol and Dashboard rebuild → `${CAIRNWORK_ROOT}/agents/analysis_executor.md`
- result interpretation, bounded follow-up and research-design decisions → `${CAIRNWORK_ROOT}/agents/research_planner.md`
- 先读取 `${CAIRNWORK_ROOT}/agents/README.md` 和对应 role contract，再结合本地
  `projects/` 规则执行；不要让 sandbox 维护第二份 role contract。

---
## User-Specific Rules

<!-- 在此添加 projects 层特定规则 -->
