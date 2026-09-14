# Analysis output and regression workflow rules

---
## 1. Scope
- 适用范围
  - 本文档沉淀 `projects/` 下 analysis output conventions、result interpretation rules、failed-run handling 与 exploratory regression workflow。
  - 目标是把结果交付相关规范从 `projects/AGENTS.md` 中抽离出来。
- precedence
  - 如具体 project / stage 有更局部规则，以局部规则为准。
  - 如用户在当前任务中明确指定命名、输出格式、报告重点，以用户要求为准。

---
## 2. Output path and naming
- 所有 `R/` 文件夹下的 analysis script，都应把结果写到同级 sibling `outputs/` 文件夹
- 例如：
  - script: `projects/<project>/<stage>/analysis/R/analysis-ai.R`
  - outputs: `projects/<project>/<stage>/analysis/outputs/`
- 不要默认把回归结果写回 `R/`、临时 notebook 目录或其他无关路径
- 在文件前部显式定义 input path 与 output path
- 路径要保持可见、可改、可被 AI 直接定位
- 默认不要用固定序号命名 table / figure
- 建议格式：
  - `table_<yymmdd>_<contents>.txt`
  - `figure_<yymmdd>_<contents>.png`
- `<contents>` 使用简短内容总结
- 如果用户在对话中提供 analysis code、专题代号或命名方案，应优先采用用户给出的方案

---
## 3. Table output conventions
- 回归结果默认用一个 `screenreg(models)` 输出整张表
- 默认把 `models` 里的模型一起组织成一张表，不要拆成多个零散输出块
- 导出时直接把 `screenreg(models)` 的结果写入输出文件
- `table_*.txt` 默认不只是裸表格：
  - 开头先写一个简短标题，直接概括这组回归想回答的问题或主要发现
  - 然后放完整 regression table
  - 表格之后补一小段 concise interpretation，只解释有信息量、尤其是 statistically significant 的结果
  - 如果没有显著结果，也要明确说明“当前规格下未得到稳健/显著结果”，不要硬写空洞总结
- 当模型包含很多 `FE` dummies、很多 task/category fixed effects、或高维 factor 展开时，默认不要把这些 nuisance coefficients 全量输出到最终 `txt`
  - 最终交付物应优先 suppress / omit 这些 FE 展开列
  - 报告重点放在用户关心的核心系数、核心交互项、以及必要的 model stats
  - 如果需要保留完整结果，完整结果可以作为附加文件或中间结果存在，但默认不应污染主输出
- 不要单独产出只有均值、`N`、`NaN` 之类信息的 `summary` 文本来代替分析结论。除非用户明确要求，否则 `summary` 只能作为补充，不能替代表格输出与结果解读

---
## 4. Failed-result handling
- 如果回归输出出现 `NaN`、主效应被吸收、严重共线、模型不收敛、关键系数无法解释，默认流程不是直接交付结果，而是：
  - 先排查 specification、`FE`、cluster、sample、变量编码
  - 必要时迭代脚本并重跑
  - 如果仍无法解决，再向用户明确报告卡点，并提出需要用户判断的选项
- 当结果“跑不通”时，agent 需要先反思并迭代，不要把明显不可解释或未识别的结果直接包装成交付物

---
## 5. Exploratory regression workflow
- 对 count / citation / adoption 这类非负、且可能有大量零值的 DV，默认增加下面的 exploration workflow：
  - 先跑基准 `OLS` / `felm` 规格
  - 对 DV 先尝试 `log(y + 1)` 版本
  - 明确检查 zero share，并在输出里报告 zero count / zero share
  - 如果 `OLS` 结果显著，默认继续尝试 count-model robustness，例如 `Poisson`；如果零值占比高，也考虑 zero-inflated family 的可行性
  - 只有在 robustness 方向与基准 `OLS` 大体一致时，才可以更有信心地汇报“结果稳健”
  - 如果 `Poisson` / zero-inflated 不适用、无法收敛、或与 `FE` 结构冲突，要在输出里明确说明，而不是静默跳过
