from __future__ import annotations

import json

from langchain_core.tools import tool

from .config import load_settings
from .knowledge import format_search_results, search_knowledge
from .market_data import (
    analyze_recent_price,
    format_quote,
    get_recent_quote,
    resolve_stock_symbol as resolve_symbol,
)
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

    from tavily import TavilyClient

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
def resolve_stock_symbol(symbol: str) -> str:
    """Resolve Chinese stock names, common typos, 6-digit A-share codes, and Yahoo symbols."""
    return format_quote(resolve_symbol(symbol))


@tool
def get_stock_price(symbol: str, period: str = "5d", interval: str = "1d") -> str:
    """Get recent stock, ETF, or index price data. A-shares use Eastmoney; others use yfinance."""
    try:
        return format_quote(get_recent_quote(symbol, period=period, interval=interval))
    except Exception as exc:
        return f"行情查询失败：{exc}"


@tool
def analyze_stock_price(symbol: str) -> str:
    """Get recent price data and produce a structured, conservative risk analysis."""
    try:
        return format_quote(analyze_recent_price(symbol))
    except Exception as exc:
        return f"行情分析失败：{exc}"


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
    resolve_stock_symbol,
    get_stock_price,
    analyze_stock_price,
    recall_investor_memory,
    save_investor_memory,
    think_tool,
]
