from __future__ import annotations

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from .config import Settings, load_settings
from .tools import (
    TOOLS,
    analyze_stock_price,
    get_stock_price,
    recall_investor_memory,
    save_investor_memory,
    search_trading_system,
    resolve_stock_symbol,
    tavily_market_search,
    think_tool,
)


SYSTEM_PROMPT = """
你是一个股票学习、研究和投资复盘助手。你的核心任务是帮助用户把“建立交易体系”的课程框架用于研究、复盘和风险控制。

工作原则：
1. 先调用 recall_investor_memory，了解用户长期偏好、风险约束、关注标的和过往复盘结论。
2. 涉及交易体系、仓位、买卖点、风控、复盘时，优先调用 search_trading_system，不要凭空总结课程。
3. 涉及当下新闻、政策、财报、宏观和行业变化时，调用 tavily_market_search，并给出来源 URL。
4. 涉及标的当前或近期价格时，先允许中文名/错别字/6位 A 股代码，用 resolve_stock_symbol、get_stock_price 或 analyze_stock_price 确认代码和行情；A 股价格以东方财富/腾讯返回为准，其他市场再用 yfinance。
5. 结论里必须区分：事实、课程框架下的推理、不确定性、需要用户自己确认的交易计划。
6. 不直接给“保证赚钱”或无条件买卖指令；所有建议都要包含失效条件、仓位风险和回撤风险。
7. 如果用户表达了稳定偏好或明确约束，可以调用 save_investor_memory 保存。
""".strip()


SUBAGENTS = [
    {
        "name": "market-researcher",
        "description": "Research current market news, company events, macro changes, and price data.",
        "prompt": "你负责实时市场研究。必须用 Tavily 或行情工具支撑事实，不要做最终投资结论。",
        "tools": [
            tavily_market_search,
            resolve_stock_symbol,
            get_stock_price,
            analyze_stock_price,
            think_tool,
        ],
    },
    {
        "name": "trading-system-analyst",
        "description": "Map a question to the private trading-system course framework.",
        "prompt": "你负责从课程知识库中找交易体系依据，提炼框架、条件、风险点和复盘问题。",
        "tools": [search_trading_system, recall_investor_memory, think_tool],
    },
    {
        "name": "risk-auditor",
        "description": "Audit position sizing, invalidation, drawdown, concentration, and uncertainty.",
        "prompt": "你负责风险复核。重点看仓位、止损/失效、情绪追涨、相关性和最坏情况。",
        "tools": [
            search_trading_system,
            get_stock_price,
            analyze_stock_price,
            recall_investor_memory,
            think_tool,
        ],
    },
]


def build_agent(settings: Settings | None = None):
    settings = settings or load_settings()
    model = init_chat_model(settings.model, temperature=0.1)
    return create_deep_agent(
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        model=model,
        subagents=SUBAGENTS,
        checkpointer=MemorySaver(),
        store=InMemoryStore(),
    )


def ask(question: str, *, thread_id: str | None = None) -> str:
    settings = load_settings()
    agent = build_agent(settings)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id or settings.thread_id}},
    )
    messages = result.get("messages", [])
    if not messages:
        return ""
    return messages[-1].content
