# Claude Code Adapter

@AGENTS.md

- Claude Code imports the same-directory `AGENTS.md` as the canonical archive instructions.
- Keep shared rules in `AGENTS.md`; put Claude Code-specific local additions in the gitignored `CLAUDE.local.md`.

---
## User-Specific Rules

若同目录存在 `CLAUDE.local.md`，在执行任务前读取并遵守其中规则；冲突时以 `.local.md` 为准。
