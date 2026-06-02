from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Article:
    article_index: int
    title: str
    url: str
    published_at: str
    study_count: str
    path: str
    text: str


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists articles (
            id integer primary key,
            article_index integer unique not null,
            title text not null,
            url text,
            published_at text,
            study_count text,
            path text,
            text text not null
        );

        create table if not exists chunks (
            id integer primary key,
            article_index integer not null,
            chunk_index integer not null,
            title text not null,
            text text not null,
            source_url text,
            unique(article_index, chunk_index)
        );

        create virtual table if not exists chunks_fts using fts5(
            title,
            text,
            content='chunks',
            content_rowid='id'
        );
        """
    )
    conn.commit()


def _clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_article_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in ["script", "style", "nav", "footer"]:
        for node in soup.select(selector):
            node.decompose()

    content = (
        soup.select_one("section.content")
        or soup.select_one("article")
        or soup.select_one(".content")
        or soup.select_one("body")
        or soup
    )
    return _clean_text(content.get_text("\n"))


def _extract_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one("h1") or soup.select_one("title")
    if title_node:
        return _clean_text(title_node.get_text(" ")) or fallback
    return fallback


def iter_course_articles(course_dir: Path) -> Iterable[Article]:
    manifest_path = course_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    articles = manifest.get("articles", [])
    if not articles:
        raise ValueError(f"No articles found in manifest: {manifest_path}")

    for idx, item in enumerate(articles, start=1):
        raw_path = item.get("savedPath") or item.get("path") or ""
        if raw_path:
            article_path = course_dir / raw_path
            if article_path.is_dir():
                article_path = article_path / "index.html"
        else:
            article_dir = item.get("articleDir") or f"article-{idx:03d}"
            article_path = course_dir / article_dir / "index.html"
        if not article_path.exists():
            raise FileNotFoundError(f"Article HTML not found for #{idx}: {item}")

        html = article_path.read_text(encoding="utf-8")
        fallback_title = item.get("title") or f"article-{idx:03d}"
        title = _extract_title(html, fallback_title)
        text = _extract_article_text(html)
        yield Article(
            article_index=int(item.get("index") or idx),
            title=title,
            url=item.get("sourceUrl") or item.get("url") or "",
            published_at=item.get("publishedAt") or item.get("published") or "",
            study_count=item.get("studyCount") or "",
            path=str(article_path),
            text=text,
        )


def chunk_text(text: str, max_chars: int = 1600, overlap: int = 180) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind("。", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, 0)
    return chunks


def ingest_course(course_dir: Path, db_path: Path) -> int:
    course_dir = course_dir.expanduser().resolve()
    if not course_dir.exists():
        raise FileNotFoundError(f"Course directory not found: {course_dir}")

    articles = list(iter_course_articles(course_dir))
    with connect(db_path) as conn:
        init_db(conn)
        conn.executescript(
            """
            delete from chunks_fts;
            delete from chunks;
            delete from articles;
            """
        )
        for article in articles:
            conn.execute(
                """
                insert into articles (
                    article_index, title, url, published_at, study_count, path, text
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.article_index,
                    article.title,
                    article.url,
                    article.published_at,
                    article.study_count,
                    article.path,
                    article.text,
                ),
            )

            for chunk_index, chunk in enumerate(chunk_text(article.text), start=1):
                cursor = conn.execute(
                    """
                    insert into chunks (
                        article_index, chunk_index, title, text, source_url
                    ) values (?, ?, ?, ?, ?)
                    """,
                    (
                        article.article_index,
                        chunk_index,
                        article.title,
                        chunk,
                        article.url,
                    ),
                )
                rowid = cursor.lastrowid
                conn.execute(
                    "insert into chunks_fts(rowid, title, text) values (?, ?, ?)",
                    (rowid, article.title, chunk),
                )
        conn.commit()
    return len(articles)


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query)
    return " OR ".join(tokens[:8]) or query


def _query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query)
    return [token for token in tokens if token.strip()]


def search_knowledge(query: str, db_path: Path, limit: int = 5) -> list[dict[str, str]]:
    if not db_path.exists():
        return [
            {
                "title": "知识库未导入",
                "text": f"请先运行 stock-learn ingest-course ... --db {db_path}",
                "source_url": "",
            }
        ]

    with connect(db_path) as conn:
        init_db(conn)
        rows: list[sqlite3.Row] = []
        try:
            rows = list(
                conn.execute(
                    """
                    select c.title, c.text, c.source_url
                    from chunks_fts f
                    join chunks c on c.id = f.rowid
                    where chunks_fts match ?
                    order by bm25(chunks_fts)
                    limit ?
                    """,
                    (_fts_query(query), limit),
                )
            )
        except sqlite3.OperationalError:
            rows = []

        if not rows:
            tokens = _query_tokens(query)
            if not tokens:
                return []
            where = " or ".join(["title like ? or text like ?" for _ in tokens])
            params: list[str | int] = []
            for token in tokens:
                like = f"%{token}%"
                params.extend([like, like])
            params.append(limit)
            rows = list(
                conn.execute(
                    f"""
                    select title, text, source_url
                    from chunks
                    where {where}
                    limit ?
                    """,
                    params,
                )
            )

    return [
        {
            "title": row["title"],
            "text": _clean_text(row["text"])[:900],
            "source_url": row["source_url"] or "",
        }
        for row in rows
    ]


def format_search_results(results: list[dict[str, str]]) -> str:
    if not results:
        return "没有检索到相关课程内容。"
    blocks = []
    for index, row in enumerate(results, start=1):
        source = f"\n来源：{row['source_url']}" if row.get("source_url") else ""
        blocks.append(f"[{index}] {row['title']}{source}\n{row['text']}")
    return "\n\n".join(blocks)
