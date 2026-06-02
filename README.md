# stock-learn

用 LangGraph / DeepAgents 搭一个股票学习、研究和交易体系复盘助手。

这个仓库只保存代码、流程文档和本地导入工具；“建立交易体系”的文章原文、图片、离线包和向量/全文索引数据库都放在本地私有目录，不提交到 GitHub。

## 能力

- 读取本地“建立交易体系”离线包，并导入为 SQLite FTS 知识库。
- 用 DeepAgents 组织主 agent、市场研究子 agent、交易体系子 agent 和风险复核子 agent。
- 接入 Tavily 做实时资讯/宏观/公司事件查询。
- 用 yfinance 查询免费股价、ETF、指数等行情数据。
- 支持长期记忆，保存你的投资偏好、风险边界、关注标的和复盘结论。

## 快速开始

```bash
cd ~/fleet/stock-learn
uv venv
source .venv/bin/activate
uv pip install -e .
cp .env.example .env
```

在 `.env` 里填入模型和 Tavily 配置。Tavily key 后面补上即可。

```bash
stock-learn ingest-course \
  "/Users/renfenghuang/Documents/Codex/2026-05-31/https-app7r5sbqh74475-h5-xet-pomoho-com/outputs/建立交易体系-离线包" \
  --db data/private/stock_learn.sqlite
```

运行助手：

```bash
stock-learn ask "先按交易体系框架，分析一下 NVDA 当前适不适合追涨？"
```

查询知识库或行情：

```bash
stock-learn search "仓位管理"
stock-learn quote NVDA
```

## 重要边界

这个项目是学习、研究和复盘助手，不是自动荐股或投资顾问。输出应该区分事实、推理和不确定性；任何交易动作都需要你自己最终判断。

## 后续更新

课程文章更新时，先重新生成本地离线包，再重新执行 `stock-learn ingest-course ...`。详细流程在 [docs/course-update-workflow.md](/Users/renfenghuang/fleet/stock-learn/docs/course-update-workflow.md)。
