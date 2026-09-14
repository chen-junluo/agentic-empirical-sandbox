# AGENTS.md

- `archive/` 用于承接 legacy materials、旧 artifacts、历史 scripts、旧 panel、旧 outputs、旧 writeup
- 这里的内容主要作为 reconstruction source，不应默认视为当前主流程
- 只要任务涉及数字化转型、reconstruction、迁移前逻辑梳理、legacy workflow 拆解，先参考本文件

---
## 1. Core boundaries

- `archive/` 不是当前 production code
- 不要默认把 `archive/` 中的代码当作最新版本
- 如需复用旧逻辑，应先与 `panel_factory/` 当前实现核对
- 不要一上来就把 `archive/` 全量重写
- 第一优先级是与原始项目保持一致，不是先追求抽象上的优雅重构

---
## 2. Reconstruction workflow

- **第一步：归档关键文件**
  - 将关键 project files 放入 `archive/`
  - 重点包括：生成代码的文件、analysis files、相关 documents、旧 panel、旧 outputs
  - 常见来源：又长又杂的 Python notebooks、旧 `.py`、旧 `.R` / `.do`、零散说明文档
- **第二步：agent 预处理 + 用户确认**
  - 先由 agent 读取 `archive/` 中的关键文件，对项目尤其是 data logic 形成初步理解
  - agent 应先按 block 切分旧文件中的逻辑，而不是要求用户手动从头拆解
  - 然后进入用户确认环节：由用户标记或确认哪些 blocks 属于 `raw -> intermediate`，哪些属于 reusable `feature`，哪些属于 final `panel`
  - 核心难点：旧项目常常通过“在旧表后增加 columns 形成新表”的方式演化，导致 intermediate files 冗余严重
  - 需要在交互中形成共识：
    - 哪些部分应保留为 base `intermediate`
    - 哪些 variables 应拆成独立 `feature`
    - final panel 应如何由 `intermediate + features` 组装而成
- **第三步：产出执行文件与任务分派**
  - 在完成 block-level 判断后，产出一个可供后续 agent 执行的文件
  - 根据工作量与复杂度，将任务适当拆成多个 blocks
  - 再把这些 blocks 拆成 `N` 个 execution files，便于分派给下游 agents 并行处理
- **第四步：结果验收与一致性保证**
  - 需要设置专门的 validation block
  - 如果验收发现问题，应继续修正，而不是直接交付
  - 最终目标是确保 consistency：最终生成的 panel 与 `archive/` 中原始项目逻辑一致，尤其要核对 merge、filter、sample boundaries、关键 variable definitions
- **第五步：代码重构与自动化**
  - 在 data construction 稳定后，再整理 analysis 部分的代码
  - 目标是参照 templates 重构现有 analysis code，使其更适合后续通过 natural language 生成、修改、运行与读取结果
- **默认原则**
  - 先恢复 minimal runnable structure，再逐步解耦

---
## User-Specific Rules

<!-- 在此添加 archive 层特定规则 -->
