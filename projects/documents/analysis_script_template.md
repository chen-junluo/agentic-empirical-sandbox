# Analysis script template and coding rules

---
## 1. Scope
- 适用范围
  - 本文档用于 `projects/` 下 empirical analysis 的默认代码模板与 coding rules。
  - 目标是让任何人只要 refer 本文档，就知道 analysis script 应该写成什么样子。
- precedence
  - 如项目子文件夹存在更低层级的 `AGENTS.md`，则以更局部规则为准。
  - 如用户在当前对话中给出更具体要求，以用户要求为准。

---
## 2. Default file form
- 默认目标不是 `.Rmd`
- 默认目标是结构化、可分块执行、输出明确的 `.R` analysis script
- 如果已有旧 `.R` 文件，优先保留原文件，再新建 AI-friendly 版本
- 除非用户明确要求，不要直接覆盖原始分析脚本
- 新文件应尽量延续用户现有的 regression style，不要强行改成完全不同的范式

---
## 3. Default script template

```r
library(dplyr)
library(lfe)
library(texreg)

# define paths
input_path <- "..."
output_dir <- "..."

# prepare analysis data
prepare_analysis_data <- function(df) {
  df %>%
    filter(...) %>%
    mutate(...)
}

# build analysis sample
df_analysis <- readRDS(input_path) %>%
  prepare_analysis_data()

# estimate models 第一行必须是y和x，x可能不止一个，control同一类型的写在一列，尽量保持精简
models <- list()
models[["baseline"]] <- felm(y ~ main_x +
    control_A1 + control_A2
    | fe1 + fe2 | 0 | cluster_level, data = df_analysis
)
models[["alt_spec"]] <- felm(y ~ main_x +
    control_A1 + control_A2 +
    control_B1 + control_B2 + control_B3
    | fe1 + fe2 | 0 | cluster_level, data = df_analysis
)

# 输出并导出同一份 regression table
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
table_title <- "Replace with a concise title"
table_interpretation <- "Replace with a concise interpretation after reviewing the estimates"
table_text <- capture.output(
  screenreg(
    models,
    stars = c(0.1, 0.05, 0.01, 0.001),
    digits = 3,
    dcolumn = TRUE,
    threeparttable = TRUE,
    fontsize = "tiny",
    include.fstatistic = TRUE,
    include.adjrs = FALSE,
    include.rsquared = FALSE,
    robust = TRUE,
    include.groups = FALSE,
    single.row = FALSE
  )
)
cat(table_text, sep = "\n")
cat("\n")

output_file <- file.path(
  output_dir,
  sprintf("table_%s_%s.txt", format(Sys.Date(), "%y%m%d"), "contents")
)
writeLines(
  c(table_title, "", table_text, "", table_interpretation),
  output_file
)
```

---
## 4. Coding rules
- model organization
  - 模型统一放入 `models <- list()`
  - 每个回归都作为 `models[["..."]]` 的命名元素
  - 对 exploratory / reporting 型回归，`models` 中每个元素默认要有清晰、可读的名字
    - 列名格式优先统一为 `DV: [因变量名]`，必要时后面再补 specification 标签
    - 例如：
      - `models[["DV: citations_3_month"]]`
      - `models[["DV: citations_3_month | post_copilot"]]`
      - `models[["DV: num_sameArchModels_nextPeriod"]]`
    - 目标是让用户直接从输出表格中看清当前列对应的因变量，以及这一列是在什么 specification 下得到的
  - 不要默认改成大量分散的 standalone model objects
- formula and structure
  - formula 中 main independent variable 必须紧跟在 `~` 后
  - control variables 放在后续换行中继续写
  - fixed effects、IV、cluster 结构直接保留在模型调用中，便于检查
- script readability
  - 每个逻辑块前必须有简短注释
  - 注释应直接说明功能，不要用装饰性分隔线
  - 路径、输出文件名、table export 都应显式写在代码中
  - 代码文件应尽量精简，不要有过多空行
  - 如果需要写说明性注释，采用中英夹杂方式；除专业术语外，尽量中文
- data manipulation
  - 数据处理优先使用 `dplyr` pipeline
  - 按功能分组整理 `mutate()`、`filter()`、`select()`
  - 能用结构化 `mutate()` 完成的内容，不要拆成过多零散赋值
  - 如果 base R 在局部场景下明显更简单，可以少量使用

---
## 5. Minimum required blocks and output rules
- 最小必备块
  - 一个 analysis script 默认至少应包含：
    - `library` 与 setup
    - input path 与 output path
    - data preparation function 或 data preparation block
    - analysis sample block
    - model estimation block
    - table output block
    - table export block
- 输出路径规范
  - 所有 `R/` 文件夹下的 analysis script，都应把结果写到同级 sibling `outputs/` 文件夹
  - 例如：
    - script: `projects/<project>/<stage>/analysis/R/analysis-ai.R`
    - outputs: `projects/<project>/<stage>/analysis/outputs/`
  - 不要默认把回归结果写回 `R/`、临时 notebook 目录或其他无关路径
  - 在文件前部显式定义 input path 与 output path
  - 路径要保持可见、可改、可被 AI 直接定位
- table output rules
  - 回归结果默认用一个 `screenreg(models)` 输出整张表
  - 默认把 `models` 里的模型一起组织成一张表，不要拆成多个零散输出块
  - 导出时直接把 `screenreg(models)` 的结果写入输出文件
- output naming
  - 默认不要用固定序号命名 table / figure
  - 建议格式：
    - `table_<yymmdd>_<contents>.txt`
    - `figure_<yymmdd>_<contents>.png`
  - `<contents>` 使用简短内容总结
  - 如果用户在对话中提供 analysis code、专题代号或命名方案，应优先采用用户给出的方案
- interpretation rules
  - `table_*.txt` 默认不只是裸表格：
    - 开头先写一个简短标题，直接概括这组回归想回答的问题或主要发现
    - 然后放完整 regression table
    - 表格之后补一小段 concise interpretation，只解释有信息量、尤其是 statistically significant 的结果
    - 如果没有显著结果，也要明确说明“当前规格下未得到稳健/显著结果”，不要硬写空洞总结
  - 当模型包含很多 FE dummies、很多 task/category fixed effects、或高维 factor 展开时，默认不要把这些 nuisance coefficients 全量输出到最终 `txt`
    - 最终交付物应优先 suppress / omit 这些 FE 展开列
    - 报告重点放在用户关心的核心系数、核心交互项、以及必要的 model stats
    - 如果需要保留完整结果，完整结果可以作为附加文件或中间结果存在，但默认不应污染主输出
  - 不要单独产出只有均值、`N`、`NaN` 之类信息的 `summary` 文本来代替分析结论。除非用户明确要求，否则 `summary` 只能作为补充，不能替代表格输出与结果解读
- failed-result handling
  - 如果回归输出出现 `NaN`、主效应被吸收、严重共线、模型不收敛、关键系数无法解释，默认流程不是直接交付结果，而是：
    - 先排查 specification、FE、cluster、sample、变量编码
    - 必要时迭代脚本并重跑
    - 如果仍无法解决，再向用户明确报告卡点，并提出需要用户判断的选项
- 当结果“跑不通”时，agent 需要先反思并迭代，不要把明显不可解释或未识别的结果直接包装成交付物
- count-like DV exploration
  - 对 count / citation / adoption 这类非负、且可能有大量零值的 DV，默认增加下面的 exploration workflow：
    - 先跑基准 `OLS` / `felm` 规格
    - 对 DV 先尝试 `log(y + 1)` 版本
    - 明确检查 zero share，并在输出里报告 zero count / zero share
    - 如果 `OLS` 结果显著，默认继续尝试 count-model robustness，例如 `Poisson`；如果零值占比高，也考虑 zero-inflated family 的可行性
    - 只有在 robustness 方向与基准 `OLS` 大体一致时，才可以更有信心地汇报“结果稳健”
    - 如果 `Poisson` / zero-inflated 不适用、无法收敛、或与 `FE` 结构冲突，要在输出里明确说明，而不是静默跳过
- agent readability enhancement
  - 如需支持频繁迭代，优先保留小型结构化对象，例如：
    - `table_specs <- list(...)`
    - `figure_specs <- list(...)`
  - 这些对象可以记录：
    - 该输出对应哪些 models
    - print 规则
    - 输出文件名
    - sample 或 specification 的简短说明
