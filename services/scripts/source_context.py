"""Article cleaning and token-budgeted source context helpers."""

import html
import math
import re

from django.utils.html import strip_tags

_CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_BOUNDARY_RE = re.compile(r"(?<=[.!?。！？])\s+|\n+")


def clean_article_content(content: str) -> str:
    """Remove markup and normalize article text without changing its meaning."""
    text = html.unescape(strip_tags(content or ""))
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Conservative tokenizer-free estimate for mixed CJK and Latin text."""
    cjk_count = len(_CJK_RE.findall(text))
    non_cjk_count = max(0, len(text) - cjk_count)
    return cjk_count + math.ceil(non_cjk_count / 4)


def fit_to_token_budget(text: str, max_tokens: int) -> str:
    """Keep complete sentence-like units within a token budget."""
    if max_tokens <= 0:
        return ""
    cleaned = clean_article_content(text)
    if estimate_tokens(cleaned) <= max_tokens:
        return cleaned

    selected: list[str] = []
    used = 0
    for unit in (part.strip() for part in _BOUNDARY_RE.split(cleaned)):
        if not unit:
            continue
        cost = estimate_tokens(unit)
        if used + cost > max_tokens:
            break
        selected.append(unit)
        used += cost

    if selected:
        return " ".join(selected)

    # A single unusually long sentence: token-aware binary search is safer than
    # a fixed character slice and works for both CJK and Latin text.
    low, high = 0, len(cleaned)
    while low < high:
        middle = (low + high + 1) // 2
        if estimate_tokens(cleaned[:middle]) <= max_tokens:
            low = middle
        else:
            high = middle - 1
    return cleaned[:low].rstrip()
