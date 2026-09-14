---
## 1. scope
- 作用
  - 沉淀 `panel_factory/` 常用的命名规范，减少文件命名、artifact naming、变量命名上的反复沟通。
  - 这是参考文档，不是 rule source；规则仍以 `AGENTS.md` 为准。
- 适用范围
  - `src/features/`
  - `src/panels/`
  - `data/features/`
  - `data/panels/`

---
## 2. file naming
- Python build scripts
  - `intermediate` builder：`build_xxx_intermediate.py`
  - `feature` builder：`build_xxx.py`
  - `panel` builder：`build_xxx_panel.py`
- artifact outputs
  - `intermediate` outputs：优先放在 `data/features/`，文件名与 builder 的核心 artifact name 对齐。
  - `feature` outputs：必须放在 `data/features/`，并严格命名为 `{grain}_{feature_name}.csv`。
  - `panel` outputs：放在 `data/panels/`，文件名应直接对应最终 panel 名称。
- naming defaults
  - 优先延续已有 `artifact names`、`merge keys`、`output boundaries`。
  - migration 中不要只为整洁而随意重命名；但 feature 一旦纳入当前 `panel_factory` contract，就必须遵守 `{grain}_{feature_name}.csv`，并联动更新所有 downstream consumers。
  - 如果重命名会影响下游 consumer，必须联动更新。

---
## 3. variable naming
- feature / column naming
  - 名称应直接表达变量含义，避免临时性、上下文依赖过强的命名。
  - 同一类变量在不同 artifacts 中尽量保持一致命名。
  - 不要轻易修改既有列名，尤其是已经作为 `merge keys`、下游回归变量、或 staged outputs contract 的列。
- merge keys
  - `merge keys` 命名应稳定、明确、可复用。
  - 如果某个 key 已被多个 `feature` / `panel` 依赖，默认将其视为 contract。
- output file naming
  - 输出文件名应与 artifact 含义一致，避免 `final_v2`、`tmp_new` 这类临时命名进入稳定流程。

---
## 4. maintenance rule
- 如果命名规范有新增、修正、或沉淀：
  - 先更新本文件。
  - 再在相关 `AGENTS.md` 中补充或调整 reference。
  - 如果本文件与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准，并尽快修正文档。
