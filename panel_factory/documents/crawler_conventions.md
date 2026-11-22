---
## 1. Scope 与 cache 位置

- 参考文档，不是 rule source；冲突时以 `AGENTS.md` 为准
- 所有 crawler cache 统一放在 `data/.cache/<feature_name>/`，用 `src/utils/cache_utils.py` 的 `cache_dir()`、`cache_store_path()` 取路径，不手写路径
- 每个 crawler 独立子目录，包含：`<feature_name>_store.sqlite` 主存储、`progress.json` 断点续传状态、`crawl_summary.json` 爬取统计
- `data/.cache/` 已 gitignored；cache 是可重建的中间产物，不是 feature output

---
## 2. Crawler 脚本

- 统一放在 `src/features/`，命名 `crawl_<grain>_<feature_name>.py`
- `crawl_*.py` 只负责取数和写 cache，不写 `data/features/`；由对应 `build_<grain>_<feature_name>.py` 读取 cache 生成 feature，并在 `PIPELINE_SPEC` 中声明
- instance-specific cache 路径在本地代码中注册，例如 `MY_FEATURE_CACHE_DIR = cache_dir("my_feature")`

---
## 3. Cache 设计原则

- 使用 sqlite 存储结构化数据，每条记录带爬取 timestamp
- 必须支持断点续传：重跑时跳过已完成的 keys，进度写入 `progress.json`
- 尽量压缩存储，只保留下游需要的字段，例如只存 abstract，不存 embedding

---
## 4. API key 与 rate limiting

- API key 只从环境变量读取，例如 `os.getenv("SEMANTIC_SCHOLAR_API_KEY")`；不写入代码、cache 或 log，并在 README 中说明如何设置
- rate limit 以 provider 官方文档和自己 API key 获批的额度为准，在脚本顶部注释中写明所用额度
- 失败请求使用 exponential backoff 重试，并设置最大重试次数
