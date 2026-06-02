from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from .agent import ask
from .config import load_settings
from .knowledge import format_search_results, ingest_course, search_knowledge
from .tools import get_stock_price


console = Console()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-learn")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest-course", help="Import a local course archive.")
    ingest.add_argument("course_dir", type=Path)
    ingest.add_argument("--db", type=Path, default=None)

    search = subparsers.add_parser("search", help="Search the local trading-system knowledge base.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)

    quote = subparsers.add_parser("quote", help="Get a recent stock/ETF/index quote.")
    quote.add_argument("symbol")
    quote.add_argument("--period", default="5d")
    quote.add_argument("--interval", default="1d")

    ask_parser = subparsers.add_parser("ask", help="Ask the DeepAgents assistant.")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--thread-id", default=None)

    return parser


def main() -> None:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "ingest-course":
        db_path = args.db or settings.db_path
        count = ingest_course(args.course_dir, db_path)
        console.print(f"已导入 {count} 篇文章到 {db_path}")
        return

    if args.command == "search":
        rows = search_knowledge(args.query, settings.db_path, limit=args.limit)
        console.print(format_search_results(rows))
        return

    if args.command == "quote":
        result = get_stock_price.invoke(
            {"symbol": args.symbol, "period": args.period, "interval": args.interval}
        )
        console.print(result)
        return

    if args.command == "ask":
        console.print(ask(args.question, thread_id=args.thread_id))
        return


if __name__ == "__main__":
    main()

