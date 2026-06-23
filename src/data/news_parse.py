"""Parse Alpaca NewsClient responses into article objects."""

from __future__ import annotations

from typing import Any


def extract_news_articles(result: Any) -> list[Any]:
    """Normalize Alpaca get_news() return value to a list of News objects or dicts."""
    data_attr = getattr(result, "data", None)
    if isinstance(data_attr, dict) and "news" in data_attr:
        return list(data_attr.get("news") or [])
    if hasattr(result, "news"):
        return list(getattr(result, "news") or [])
    if isinstance(result, dict):
        return list(result.get("news") or [])
    return []


def article_symbols(article: Any) -> list[str]:
    if isinstance(article, dict):
        return list(article.get("symbols") or [])
    return list(getattr(article, "symbols", None) or [])


def article_headline(article: Any) -> str:
    if isinstance(article, dict):
        return article.get("headline", "") or ""
    return getattr(article, "headline", "") or ""


def article_to_headline_fields(article: Any) -> dict[str, Any]:
    """Convert a News model or raw dict into normalized headline fields."""
    if isinstance(article, dict):
        return {
            "symbols": list(article.get("symbols") or []),
            "headline": article.get("headline", ""),
            "source": article.get("source", ""),
            "created_at": str(article.get("created_at", "")),
        }
    return {
        "symbols": list(article.symbols) if getattr(article, "symbols", None) else [],
        "headline": getattr(article, "headline", ""),
        "source": getattr(article, "source", ""),
        "created_at": str(getattr(article, "created_at", "")),
    }
