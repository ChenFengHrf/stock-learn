# stock-learn skill

Use this skill when updating the private “建立交易体系” course archive, ingesting it into the local stock-learning knowledge base, or running the LangGraph / DeepAgents stock assistant.

## Workflow

1. Never commit paid course text, images, generated offline archives, or SQLite knowledge indexes.
2. Export or refresh the course archive from the logged-in browser session.
3. Verify the local archive:
   - `index.html` opens offline.
   - `manifest.json` lists all articles.
   - Article images are local files and render correctly.
4. Ingest the archive:

```bash
stock-learn ingest-course "/path/to/建立交易体系-离线包" --db data/private/stock_learn.sqlite
```

5. Run a smoke test:

```bash
stock-learn search "仓位管理"
stock-learn ask "用交易体系框架分析一下我现在追涨的风险"
```

6. If Tavily is needed, ensure `TAVILY_API_KEY` exists in `.env`.

## Agent design

- Main agent: coordinates the answer and asks subagents for research.
- Trading-system analyst: searches the local course knowledge base first.
- Market researcher: uses Tavily and stock price tools for current information.
- Risk auditor: checks position sizing, invalidation, drawdown, and uncertainty.
- Memory: stores stable user preferences, risk constraints, watchlists, and repeated review findings.

