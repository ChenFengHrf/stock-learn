from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_path: Path
    model: str
    tavily_api_key: str | None
    user_id: str
    thread_id: str


def load_settings() -> Settings:
    db_path = Path(os.getenv("STOCK_LEARN_DB", "data/private/stock_learn.sqlite"))
    if not db_path.is_absolute():
        db_path = _repo_root() / db_path

    return Settings(
        db_path=db_path,
        model=os.getenv("STOCK_LEARN_MODEL", "openai:gpt-4.1-mini"),
        tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
        user_id=os.getenv("STOCK_LEARN_USER_ID", "default"),
        thread_id=os.getenv("STOCK_LEARN_THREAD_ID", "default"),
    )

