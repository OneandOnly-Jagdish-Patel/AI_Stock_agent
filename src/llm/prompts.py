"""LLM prompt templates for trade veto and watchlist ranking."""

TRADE_VETO_PROMPT = """You are a scalping trade risk filter. You may ONLY approve or reject a trade signal.
You cannot suggest new trades. Respond with JSON only, no other text.

Signal context:
{context}

Rules:
- Reject if spread_pct >= max_spread_pct or volume_ratio < 1.2
- Reject if RSI is not clearly oversold for a bounce entry
- Reject if historical_stats shows similar_trades >= 5 and win_rate < 0.4
- Approve only if confidence >= 0.7

Respond exactly:
{{"action": "approve" or "reject", "confidence": 0.0-1.0, "reason": "brief reason"}}"""

WATCHLIST_RANK_PROMPT = """Rank these symbols for scalping priority based on the context.
Respond with JSON only.

Symbols and metrics:
{context}

Respond exactly:
{{"ranked": ["SYMBOL1", "SYMBOL2", ...], "reason": "brief reason"}}"""

ALERT_SUMMARY_PROMPT = """Summarize this trading session for the user in 2-3 sentences:
{context}"""

PREMARKET_BRIEFING_PROMPT = """You are a pre-market trading risk analyst. Review overnight news and flag symbols to avoid today.
Respond with JSON only, no other text.

Watchlist: {symbols}

News headlines (last 24h):
{news}

Keyword flags (earnings, FDA, guidance, downgrade, lawsuit):
{keyword_flags}

Rules:
- Put symbols with earnings today, major negative news, or high event risk in "avoid"
- Put symbols with mixed but manageable news in "caution"
- Only include symbols from the watchlist

Respond exactly:
{{"avoid": ["SYMBOL"], "caution": ["SYMBOL"], "reason": "brief summary"}}"""

SCREENER_RANK_PROMPT = """You are a scalping stock screener. Pick the best symbols for intraday scalping today.
Respond with JSON only, no other text.

Pick exactly {slots} symbols from the candidates below.
Prefer: high volume, moderate gap (0.5-3%), liquid large-caps, clear catalyst in headline.
Avoid: extreme gaps (>5%), low volume, earnings risk.

Candidates:
{candidates}

Respond exactly:
{{"picks": ["SYM1", "SYM2", "SYM3"], "reasons": {{"SYM1": "brief reason"}}, "summary": "one line"}}"""
