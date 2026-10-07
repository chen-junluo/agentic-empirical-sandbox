# agentic-empirical-sandbox

[English README](README.md)

一个紧凑、agent-native 的 empirical research workspace template，支持 Codex 和 Claude Code 重建 legacy research workflow。

## 用途

sandbox 将 legacy sources、可复用 data construction 和 project-specific research 分开：

- `archive/`：作为 reconstruction source 的旧 scripts、panels、outputs 和 writeups。
- `panel_factory/`：围绕 `intermediate + features -> panel` 组织的 shared data construction。
- `projects/`：下游 analysis、figures、tables 和 writing。

workflow 不反复 mutate 一个大表，而是分离 reusable base intermediates、compact keyed features 和通过 late merge 生成的 final panels。这样可以逐步重建 legacy workflow，并避免 project-specific logic 混入 shared pipeline。

## 仓库结构

```text
agentic-empirical-sandbox/
├── AGENTS.md
├── CLAUDE.md
├── agents/
│   └── README.md              # 薄引用层；contracts 在 Cairnwork
├── archive/
│   ├── AGENTS.md
│   └── CLAUDE.md
├── panel_factory/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── data/
│   ├── documents/
│   ├── notebooks/
│   └── src/
├── projects/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── documents/
│   └── project_template_IT_investment/
└── scripts/
```

先把 legacy sources 放进 `archive/`，inventory 其中的 data logic，在 `panel_factory/` 重建 reusable construction，并把 regressions 和 writing 留在 `projects/`。先恢复 minimal runnable workflow，再优化抽象。

## Cairnwork integration

三个 canonical role contract 统一维护在独立的 Cairnwork repository 中。将
`CAIRNWORK_ROOT` 指向该 checkout，然后读取
`$CAIRNWORK_ROOT/agents/README.md` 和对应的 role contract。本仓库只提供
workspace-specific 的边界、project context 和本地 routing。

如果项目使用 Cairnwork，可以用下面的一句话初始化某个 project：

```bash
python3 <CAIRNWORK_ROOT>/scripts/init_project.py \
  --root projects/<project-directory>
```

具体的安全检查、命令链和 handoff 以 Cairnwork 中的 role contract 为准；本仓库的
`AGENTS.md` 只补充本地边界和 routing。

## Codex 与 Claude Code 指令

各层都以 `AGENTS.md` 作为 tool-neutral canonical rule source：

- 根目录 `AGENTS.md`：workspace architecture、边界和任务路由。
- `archive/AGENTS.md`：legacy reconstruction。
- `panel_factory/AGENTS.md`：shared data-pipeline contracts。
- `projects/AGENTS.md`：下游 analysis 和 writing。

[Codex 会分层发现 `AGENTS.md`](https://developers.openai.com/codex/guides/agents-md/)，从 project root 读取到 working directory，更局部的规则后生效。一般任务从仓库根目录启动；如果希望某个子目录规则进入初始 instruction chain，可从相应子目录启动 Codex。

[Claude Code 读取 `CLAUDE.md` 并支持 `@path` import](https://code.claude.com/docs/en/memory)。每个 thin `CLAUDE.md` adapter 都用 `@AGENTS.md` 引用同层 canonical rules，不复制长规则。Claude Code 启动时加载适用的父目录指令，并在处理子目录内容时发现子目录指令。

本轮明确只支持 Codex 和 Claude Code。

## 受保护的定制边界

每个允许定制的 instruction file 都必须且只能包含一个 marker：

```markdown
## User-Specific Rules
```

- marker 之前：upstream-managed public rules。
- marker 本身及其后每一个 byte：user-specific content。

共享、tool-neutral 的自定义规则应写在 `AGENTS.md` marker 下方；`CLAUDE.md` marker 只放 Claude Code-specific additions。updater 会验证 marker 精确出现一次，并逐字节保留整个 user-specific section；marker 缺失或重复会立即停止更新。

## 安全的手动更新

updater 只同步 [`scripts/template_manifest.json`](scripts/template_manifest.json) 明确列出的路径。未列出的文件、实际研究数据、`panel_factory/data/` 中明确列出的 `.gitkeep` 之外的内容、用户创建的 project content，以及 instruction files 之外的 archive materials 都不在 managed scope 内；updater 不会通过递归扫描扩大范围。

如果这是一个 fork，请先确认公开仓库 URL，再自行添加 `upstream` remote：

```bash
git remote add upstream CONFIRMED_PUBLIC_REPOSITORY_URL
```

`CONFIRMED_PUBLIC_REPOSITORY_URL` 是需要替换的标签，不是本 template 提供的真实 URL。

先预览三方比较，不修改 working-tree files：

```bash
python3 scripts/update_template.py check
```

确认后应用无冲突更新，并检查 diff：

```bash
python3 scripts/update_template.py apply
git diff
```

`check` 和 `apply` 都会 fetch `upstream/main`。报告区分 `unchanged`、`safe update`、`add`、`conflict`、`protected` 和 `manual review`。只要任一 managed file 冲突，`apply` 就零写入。upstream 删除或重命名只提示人工复核，不自动删除、移动或重命名。成功的 apply 会原子替换安全文件、更新 `.agentic-sandbox-state.json`，但不会 commit。

三方判断与测试命令详见 [`scripts/README.md`](scripts/README.md)。

## 自动生成的 pipeline dependency map

每个 `panel_factory/src/**/build_*.py` 都通过 structured header 声明 artifact type、grain、merge keys、inputs、output、columns 和 core logic。dependency generator 会验证这些 contracts，并在 [`panel_factory/documents/pipeline_dependency_table.md`](panel_factory/documents/pipeline_dependency_table.md) 中生成 Mermaid DAG、artifact table 和逐项 reference。

```bash
python3 scripts/update_dependency_docs.py check
python3 scripts/update_dependency_docs.py write
```

`check` 只检查、不改文档；它会报告 header 缺失或格式错误、命名违规、重复 artifact/output、无法解析的 generated input、dependency cycle 和过期的 map。`write` 会先执行同样的完整验证，再原子刷新 map。这样人和 agent 都能先读 dependency map 理解 pipeline，不必每次从全部 implementation files 重新推断依赖。

## Tool-neutral 启动 prompt

```text
请先读取当前目录适用的 repository instructions，并在操作前检查相关的 archive、panel_factory 或 projects 材料。保留 raw data 和既有 artifact contracts，只进行本次请求范围内的修改，并在确认验证结果后再报告完成。
```

## 自带 placeholders

仓库包含 `panel_factory/` 下的最小 example builders、paths 和 data-directory `.gitkeep`，以及 project dashboard notes 和各 stage 的 writeup placeholders。它们是起点，不是真实研究数据。

## License

MIT
