"""Tests for content hash generation."""

from services.news.content_hash import ContentHashService


class TestContentHashService:
    def setup_method(self) -> None:
        self.service = ContentHashService()

    def test_same_content_produces_same_hash(self) -> None:
        content = "Hello   World\n\nFrom RSS"
        hash_one = self.service.generate_hash(content)
        hash_two = self.service.generate_hash("hello world from rss")
        assert hash_one == hash_two

    def test_different_content_produces_different_hash(self) -> None:
        hash_one = self.service.generate_hash("Article A")
        hash_two = self.service.generate_hash("Article B")
        assert hash_one != hash_two

    def test_empty_content_uses_title_fallback(self) -> None:
        hash_from_title = self.service.generate_hash("", fallback_title="My Title")
        hash_from_content = self.service.generate_hash("my title")
        assert hash_from_title == hash_from_content

    def test_hash_is_sha256_hex(self) -> None:
        content_hash = self.service.generate_hash("sample")
        assert len(content_hash) == 64
        assert all(char in "0123456789abcdef" for char in content_hash)

    def test_normalize_content_collapses_whitespace(self) -> None:
        normalized = self.service.normalize_content("  Foo   Bar  ")
        assert normalized == "foo bar"
