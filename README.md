# agentic-empirical-sandbox

[中文说明](README-zh.md)

A compact, agent-native workspace template for reconstructing empirical research workflows with Codex or Claude Code.

## Purpose

The sandbox separates legacy sources, reusable data construction, and project-specific research:

- `archive/`: legacy scripts, panels, outputs, and writeups used as reconstruction sources.
- `panel_factory/`: shared data construction built around `intermediate + features -> panel`.
- `projects/`: downstream analysis, figures, tables, and writing.

Instead of repeatedly mutating one large table, the workflow keeps reusable base intermediates, compact keyed features, and final late-merged panels separate. This makes legacy reconstruction incremental and keeps project-specific logic out of the shared pipeline.

## Repository structure

```text
agentic-empirical-sandbox/
├── AGENTS.md
├── CLAUDE.md
├── agents/
│   └── README.md              # thin pointer; contracts live in Cairnwork
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

Start by placing legacy sources in `archive/`, inventorying their data logic, rebuilding reusable construction in `panel_factory/`, and keeping regressions and writing in `projects/`. Recover a minimal runnable workflow before optimizing abstractions.

## Cairnwork integration

The canonical three role contracts are maintained in the separate Cairnwork
repository. Set `CAIRNWORK_ROOT` to that checkout, then read
`$CAIRNWORK_ROOT/agents/README.md` and the role contract that matches the task.
This repository contributes only workspace-specific boundaries and project
context.

For a project that uses Cairnwork, the initializer command is:

```bash
python3 <CAIRNWORK_ROOT>/scripts/init_project.py \
  --root projects/<project-directory>
```

The Cairnwork role contracts specify the safety checks and handoffs around this
command; this repository's `AGENTS.md` files add local routing and boundaries.

## Codex and Claude Code instructions

`AGENTS.md` is the tool-neutral canonical rule source at every level:

- Root `AGENTS.md` defines the workspace architecture, boundaries, and task routing.
- `archive/AGENTS.md` defines legacy reconstruction.
- `panel_factory/AGENTS.md` defines shared data-pipeline contracts.
- `projects/AGENTS.md` defines downstream analysis and writing.

[Codex discovers layered `AGENTS.md` files](https://developers.openai.com/codex/guides/agents-md/) from the project root toward the working directory, with more local instructions applied later. Start Codex from the repository root for general work or from a relevant subdirectory when that directory's rules should be in the initial instruction chain.

[Claude Code reads `CLAUDE.md` files and supports `@path` imports](https://code.claude.com/docs/en/memory). Each thin `CLAUDE.md` adapter imports its same-directory `AGENTS.md` with `@AGENTS.md`; shared rules are not duplicated. Claude Code loads applicable parent instructions at launch and discovers child-directory instructions when it works in those directories.

This release intentionally supports only Codex and Claude Code.

## Protected customization boundary

Every managed instruction file is fully upstream-managed and ends with exactly one marker:

```markdown
## User-Specific Rules
```

Below the marker is a single pointer line telling the agent to read the same-directory `*.local.md` file, which is gitignored and holds your private rules. Put shared, tool-neutral rules in `AGENTS.local.md` and Claude Code-only additions in `CLAUDE.local.md`; when they conflict with public rules, `.local.md` wins.

The updater replaces the whole instruction file and never reads or writes `*.local.md`. It validates that the marker exists exactly once. If anything other than the pointer line or HTML comments sits below the marker (for example rules written under the old layout), the update stops with a conflict; move that content into the matching `.local.md` and rerun.

## Safe manual updates

The updater synchronizes only paths explicitly listed in [`scripts/template_manifest.json`](scripts/template_manifest.json). Unlisted files, actual research data, `panel_factory/data/` except its named `.gitkeep` placeholders, user-created project content, and archive materials other than instruction files are outside its managed scope. The updater never recursively expands that scope.

If this is a fork, first confirm the public repository URL and add it yourself as the `upstream` remote:

```bash
git remote add upstream CONFIRMED_PUBLIC_REPOSITORY_URL
```

`CONFIRMED_PUBLIC_REPOSITORY_URL` is a label to replace, not a repository URL supplied by this template.

Preview the three-way comparison without changing working-tree files:

```bash
python3 scripts/update_template.py check
```

Apply only conflict-free updates, then review them:

```bash
python3 scripts/update_template.py apply
git diff
```

`check` and `apply` fetch `upstream/main`. Reports distinguish `unchanged`, `safe update`, `add`, `conflict`, `protected`, and `manual review`. If any managed file conflicts, `apply` writes nothing. Upstream deletions or renames are reported for manual review and are never applied automatically. Successful apply operations atomically replace safe files, update `.agentic-sandbox-state.json`, and never commit.

See [`scripts/README.md`](scripts/README.md) for the merge rules and test command.

## Generated pipeline dependency map

Every `panel_factory/src/**/build_*.py` file keeps its top bullet comments and declares a top-level `PIPELINE_SPEC` with the builder, stage, grain, canonical artifact keys, merge keys, and direct upstream builders. The AST-based generator validates those contracts and produces a compact Builder Matrix plus Builder Cards in [`panel_factory/documents/pipeline_dependency_table.md`](panel_factory/documents/pipeline_dependency_table.md).

```bash
python3 scripts/update_dependency_docs.py check
python3 scripts/update_dependency_docs.py write
```

`check` reports metadata warnings and a stale table without changing the document. `write` performs the same validation before atomically refreshing the table. Builder metadata is read with `ast` so documentation generation does not import or execute pipeline code.

## Tool-neutral starter prompt

```text
Read the repository instructions that apply to the current directory. Inspect the relevant archive, panel_factory, or projects materials before acting. Preserve raw data and existing artifact contracts, make only the requested changes, and validate the result before reporting completion.
```

## Included placeholders

The repository includes minimal example builders and paths under `panel_factory/`, data-directory `.gitkeep` files, project dashboard notes, and stage writeup placeholders. They are starting points, not real research data.

## License

MIT
