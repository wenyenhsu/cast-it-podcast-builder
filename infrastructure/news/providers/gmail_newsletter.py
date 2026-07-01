"""Gmail newsletter news provider via Gmail API (OAuth2)."""

import base64
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from django.conf import settings

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from services.news.validation import ArticleValidator

logger = logging.getLogger(__name__)

_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _build_gmail_service() -> Any:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri=_TOKEN_URI,
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=_GMAIL_SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode_body(data: str) -> str:
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _extract_plain_text(payload: dict[str, Any]) -> str:
    """Recursively extract plain text from a MIME payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return _decode_body(body_data)

    if mime_type == "text/html" and body_data:
        from bs4 import BeautifulSoup

        html = _decode_body(body_data)
        return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)

    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text

    return ""


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "").strip()
    return ""


def _parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _sender_name(from_header: str) -> str:
    """Extract display name from 'Name <email>' or fall back to address."""
    match = re.match(r"^(.+?)\s*<[^>]+>$", from_header)
    if match:
        return match.group(1).strip().strip('"')
    return from_header.split("@")[0]


class GmailNewsletterProvider(BaseNewsProvider):
    """Collects newsletter emails from Gmail via the Gmail API (OAuth2)."""

    def __init__(
        self,
        config: ProviderConfig,
        validator: ArticleValidator | None = None,
    ) -> None:
        super().__init__(config, validator)
        self._query = (config.extra or {}).get("gmail_query", settings.GMAIL_QUERY)
        self._limit = config.max_articles_per_import or 50

    def collect(self) -> list[ArticleDTO]:
        if not all(
            [settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]
        ):
            logger.error(
                "Gmail credentials not configured",
                extra={"event": "provider_error", "provider": "GmailNewsletterProvider"},
            )
            return []

        logger.info(
            "Provider started",
            extra={
                "event": "provider_started",
                "provider": "GmailNewsletterProvider",
                "source": self.source_name,
                "query": self._query,
            },
        )

        try:
            service = _build_gmail_service()
            result = (
                service.users()
                .messages()
                .list(userId="me", q=self._query, maxResults=self._limit)
                .execute()
            )
            messages = result.get("messages", [])

            raw_messages = []
            for msg in messages:
                full = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                raw_messages.append(full)

        except Exception:
            logger.exception(
                "Gmail API call failed",
                extra={"event": "provider_error", "provider": "GmailNewsletterProvider"},
            )
            return []

        articles = self.normalize(raw_messages)

        logger.info(
            "Provider finished",
            extra={
                "event": "provider_finished",
                "provider": "GmailNewsletterProvider",
                "source": self.source_name,
                "articles_collected": len(articles),
            },
        )
        return articles

    def normalize(self, raw_data: Any) -> list[ArticleDTO]:
        articles: list[ArticleDTO] = []

        for msg in raw_data:
            try:
                headers = msg.get("payload", {}).get("headers", [])
                title = _header(headers, "Subject") or "(no subject)"
                from_header = _header(headers, "From")
                author = _sender_name(from_header)
                published_at = _parse_date(_header(headers, "Date"))
                content = _extract_plain_text(msg.get("payload", {}))

                # Use a gmail:// URI so dedup hash works even without a web URL
                msg_id = msg.get("id", "")
                url = f"gmail://message/{msg_id}"

                article = ArticleDTO(
                    title=title,
                    source=self.source_name,
                    url=url,
                    author=author,
                    published_at=published_at,
                    language=self.config.language,
                    content=content,
                )

                if self.validate(article):
                    articles.append(article)

            except Exception:
                logger.exception(
                    "Failed to normalize Gmail message",
                    extra={"event": "normalization_error", "provider": "GmailNewsletterProvider"},
                )

        return articles

    def health_check(self) -> bool:
        if not all(
            [settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]
        ):
            return False

        try:
            service = _build_gmail_service()
            service.users().getProfile(userId="me").execute()
            return True
        except Exception:
            logger.exception(
                "Gmail health check failed",
                extra={"event": "health_check_failed", "provider": "GmailNewsletterProvider"},
            )
            return False
