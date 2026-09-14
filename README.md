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

Every customizable instruction file contains exactly one marker:

```markdown
## User-Specific Rules
```

- Before the marker: upstream-managed public rules.
- The marker and every byte after it: user-specific content.

Add shared, tool-neutral rules below the marker in `AGENTS.md`; reserve the `CLAUDE.md` marker for Claude Code-only additions. The updater validates that the marker exists exactly once and preserves the entire user-specific section byte-for-byte. A missing or repeated marker stops the update.

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

Every `panel_factory/src/**/build_*.py` file declares a structured header with its artifact type, grain, merge keys, inputs, output, columns, and core logic. The dependency generator validates those contracts and produces a Mermaid DAG, artifact table, and per-artifact reference in [`panel_factory/documents/pipeline_dependency_table.md`](panel_factory/documents/pipeline_dependency_table.md).

```bash
python3 scripts/update_dependency_docs.py check
python3 scripts/update_dependency_docs.py write
```

`check` reports missing or malformed headers, naming violations, duplicate artifacts or outputs, unresolved generated inputs, dependency cycles, and a stale map without changing the document. `write` performs the same validation before atomically refreshing the map. This lets people and agents inspect the pipeline without repeatedly reconstructing dependencies from every implementation file.

## Tool-neutral starter prompt

```text
Read the repository instructions that apply to the current directory. Inspect the relevant archive, panel_factory, or projects materials before acting. Preserve raw data and existing artifact contracts, make only the requested changes, and validate the result before reporting completion.
```

## Included placeholders

The repository includes minimal example builders and paths under `panel_factory/`, data-directory `.gitkeep` files, project dashboard notes, and stage writeup placeholders. They are starting points, not real research data.

## License

MIT
