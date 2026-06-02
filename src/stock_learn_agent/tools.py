from __future__ import annotations

import json
from typing import Any

import yfinance as yf
from langchain_core.tools import tool
from tavily import TavilyClient

from .config import load_settings
from .knowledge import format_search_results, search_knowledge
from .memory import format_memories, save_memory, search_memories


@tool
def search_trading_system(query: str, limit: int = 5) -> str:
    """Search the private local trading-system course knowledge base."""
    settings = load_settings()
    results = search_knowledge(query, settings.db_path, limit=limit)
    return format_search_results(results)


@tool
def tavily_market_search(query: str, topic: str = "finance", max_results: int = 5) -> str:
    """Search current market, macro, company, and policy information using Tavily."""
    settings = load_settings()
    if not settings.tavily_api_key:
        return "TAVILY_API_KEY 未配置。请在 .env 中补充后再查询实时资讯。"

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(
        query=query,
        topic=topic,
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
    )
    return json.dumps(response, ensure_ascii=False, indent=2)


@tool
def get_stock_price(symbol: str, period: str = "5d", interval: str = "1d") -> str:
    """Get recent stock, ETF, or index price data using the free yfinance API."""
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period, interval=interval, auto_adjust=False)
    if history.empty:
        return f"没有查到 {symbol} 的行情数据。可以尝试换成 Yahoo Finance 标准代码。"

    latest = history.tail(1).iloc[0]
    info: dict[str, Any] = {}
    try:
        fast_info = ticker.fast_info
        info = {
            "currency": getattr(fast_info, "currency", None),
            "exchange": getattr(fast_info, "exchange", None),
            "last_price": getattr(fast_info, "last_price", None),
            "market_cap": getattr(fast_info, "market_cap", None),
        }
    except Exception:
        info = {}

    payload = {
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "latest_bar": {
            "date": str(history.tail(1).index[0]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
        },
        "fast_info": info,
        "recent_bars": [
            {
                "date": str(index),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for index, row in history.tail(10).iterrows()
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def recall_investor_memory(query: str = "", limit: int = 8) -> str:
    """Recall long-term investor memory such as preferences, constraints, watchlists, and reviews."""
    settings = load_settings()
    rows = search_memories(settings.db_path, user_id=settings.user_id, query=query, limit=limit)
    return format_memories(rows)


@tool
def save_investor_memory(
    topic: str,
    content: str,
    kind: str = "preference",
    importance: int = 3,
) -> str:
    """Save stable investor memory for future sessions."""
    settings = load_settings()
    memory_id = save_memory(
        settings.db_path,
        user_id=settings.user_id,
        kind=kind,
        topic=topic,
        content=content,
        importance=importance,
    )
    return f"已保存长期记忆 #{memory_id}: [{kind}] {topic}"


@tool
def think_tool(reflection: str) -> str:
    """Write down private reasoning checkpoints before making a market or risk conclusion."""
    return f"已记录思考检查点：{reflection}"


TOOLS = [
    search_trading_system,
    tavily_market_search,
    get_stock_price,
    recall_investor_memory,
    save_investor_memory,
    think_tool,
]

