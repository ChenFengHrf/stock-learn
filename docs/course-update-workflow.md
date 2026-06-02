# 建立交易体系离线包更新流程

目标：把已登录页面里的课程文章保存为本地离线包，再导入 `stock-learn` agent 的本地知识库。课程原文和图片只保存在本机，不提交 GitHub。

## 当前已验证的离线包

```text
/Users/renfenghuang/Documents/Codex/2026-05-31/https-app7r5sbqh74475-h5-xet-pomoho-com/outputs/建立交易体系-离线包
```

这个目录里有：

- `index.html`：本地课程目录。
- `manifest.json`：文章清单、标题、来源 URL、保存路径。
- 每篇文章自己的 HTML 和图片资源。

## 以后文章更新时怎么做

1. 先用已登录的 in-app browser 打开课程页，确认能看到新文章。
2. 重新跑课程导出脚本，导出为新的本地离线包。导出时要用浏览器登录态，不要直接用匿名 `curl`。
3. 导出脚本需要收集课程目录里的文章链接，逐篇打开文章页。
4. 抽取正文时优先抓文章主内容区，图片优先使用真实图片地址，例如 `data-src`、`src`、懒加载字段。
5. 下载图片到文章本地目录，并把 HTML 里的图片链接重写成本地相对路径。
6. 做离线校验：打开本地 `index.html`，确认文章可读；检查 `img src` 不再指向远程未下载图片。
7. 导入 agent 知识库：

```bash
cd ~/fleet/stock-learn
stock-learn ingest-course \
  "/path/to/新的建立交易体系-离线包" \
  --db data/private/stock_learn.sqlite
```

## 为什么不把离线包提交到仓库

这个课程内容属于登录后可见的文章资源。为了避免把付费内容公开到 GitHub，仓库只保存：

- 导入和检索代码。
- DeepAgents / LangGraph agent 代码。
- 更新流程文档。
- 本地私有数据目录约定。

下面这些内容默认被 `.gitignore` 忽略：

- `data/private/`
- `data/**/*.sqlite`
- `outputs/`
- 含课程原文和图片的离线包目录。

## 导出脚本的关键检查点

- 目录页文章数量要和 manifest 数量一致。
- 每篇文章标题、来源 URL、保存路径都写入 manifest。
- 图片文件必须存在，HTML 中不能残留失效链接。
- 如果页面有防盗链或懒加载，先用浏览器上下文取最终图片 URL，再下载。
- 更新后重新跑 `stock-learn search "仓位管理"` 这类查询，确认知识库能搜到新内容。

