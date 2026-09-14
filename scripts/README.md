# Template updater

The updater performs a manual, allowlisted three-way merge from `upstream/main` using only the Python standard library.

## Commands

```bash
python3 scripts/update_template.py check
python3 scripts/update_template.py apply
```

Both commands fetch `upstream/main`. `check` reads Git objects and the working tree but does not change working-tree files or updater state. `apply` repeats the full preflight and writes only when no managed file has a conflict.

If `upstream` is missing, the updater stops and prints the setup command. It never creates or changes remotes. Confirm the public repository URL before replacing the label in:

```bash
git remote add upstream CONFIRMED_PUBLIC_REPOSITORY_URL
```

## Managed scope

[`template_manifest.json`](template_manifest.json) is an explicit path allowlist. The updater reads the local manifest for the current run and never recursively scans for more managed files. This prevents a new upstream manifest from silently expanding the current update's scope.

The allowlist covers public instruction files, Claude Code adapters, READMEs, updater files, public documents, and named template placeholders. Everything else is protected, including:

- user-added and unlisted files;
- actual research data and `panel_factory/data/` contents other than named `.gitkeep` placeholders;
- user-created or populated projects beyond explicitly named template placeholders;
- archive materials;
- instruction content beginning with `## User-Specific Rules`.

## Three-way decisions

The baseline is the `upstream_commit` recorded in `.agentic-sandbox-state.json`. Before the first successful apply, the updater uses the Git merge base between `HEAD` and `upstream/main`; it stops if neither baseline is available. State also records the allowlist used for that apply. If an accepted manifest update introduces a new path, the following run treats it as newly managed, so an upstream placeholder can be added without letting the prior run expand its scope.

- `unchanged`: upstream managed content has not changed and local managed content still matches, or the local file already matches upstream.
- `safe update`: upstream changed while local managed content still equals the baseline.
- `add`: an allowlisted upstream path is new and absent locally.
- `conflict`: local and upstream managed content both changed relative to the baseline, a local path is not a regular file, a managed path or one of its parent directories is a symbolic link, or an instruction marker is invalid.
- `protected`: a local-only change or pre-existing local path will be left untouched.
- `manual review`: upstream removed or renamed a path; the updater will not delete, move, or rename the local file.

For instruction files, only bytes before the exact marker are compared:

```markdown
## User-Specific Rules
```

The marker and every byte after it come from the local file unchanged. Local, baseline, and upstream versions must each contain exactly one marker whenever that version exists. Missing or repeated markers are conflicts.

The updater does not use symlinks for synchronization and never follows them for managed local paths. If a managed path itself, or any repository-relative parent directory on that path, is a symlink, both `check` and `apply` report a conflict. Because conflicts fail the complete preflight, `apply` leaves every working-tree file and the updater state unchanged.

The local manifest and updater state are trust metadata, so a symlink at either of those paths is rejected before its target is read.

If any conflict exists, `apply` changes no working-tree file and does not update state. Otherwise it stages all output in same-directory temporary files, atomically replaces `safe update` and `add` targets, records the fetched commit, and asks the user to run `git diff`. It never commits.

Upstream deletions remain local and are reported once for manual review. Advancing the baseline after a conflict-free apply does not delete that protected local copy.

## Tests

```bash
python3 scripts/test_update_template.py
```

The integration suite creates isolated temporary Git repositories. It covers no-op checks, safe updates, conflicts and zero-write aborts, byte-preserved instruction suffixes, protected user content, new placeholders, upstream deletions, idempotency, invalid markers, managed-path symlink conflicts, and trust-metadata symlink rejection. It does not modify this repository.

## Pipeline dependency map

The dependency-map generator reads structured headers from every `panel_factory/src/**/build_*.py` file. It validates artifact contracts and generates the Mermaid graph, artifact table, and detailed contracts in `panel_factory/documents/pipeline_dependency_table.md`.

```bash
python3 scripts/update_dependency_docs.py check
python3 scripts/update_dependency_docs.py write
python3 scripts/test_update_dependency_docs.py
```

`check` is read-only and exits nonzero when a header is invalid or the generated map is stale. `write` validates the complete graph before atomically replacing the map. Treat builder headers as the canonical dependency metadata and do not hand-edit the generated map.
