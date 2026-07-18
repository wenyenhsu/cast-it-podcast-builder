"""Tests for token-budgeted article source preparation."""

from services.scripts.source_context import (
    clean_article_content,
    estimate_tokens,
    fit_to_token_budget,
)


def test_clean_article_content_removes_html_and_whitespace() -> None:
    assert clean_article_content("<p>Hello   world</p>\n\n\n<p>Again</p>") == (
        "Hello world\n\nAgain"
    )


def test_fit_to_token_budget_uses_token_estimate_and_sentence_boundaries() -> None:
    text = "First complete sentence. Second complete sentence. Third sentence."
    result = fit_to_token_budget(text, estimate_tokens("First complete sentence."))

    assert result == "First complete sentence."
    assert estimate_tokens(result) <= estimate_tokens("First complete sentence.")


def test_cjk_token_estimate_is_not_latin_character_division() -> None:
    assert estimate_tokens("這是一段中文內容") >= 8
