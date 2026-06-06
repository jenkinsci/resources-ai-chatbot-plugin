"""Unit tests for docs_crawler module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from data.collection.docs_crawler import (
    CrawlState,
    normalize_url,
    is_valid_url,
    extract_page_content_container,
    _fetch_html,
    fetch_and_process_page,
    worker,
)


@pytest.fixture
def state():
    """Provide a fresh CrawlState for each test."""
    return CrawlState()


# ── normalize_url ────────────────────────────────────────────────


def test_normalize_url_adds_trailing_slash():
    """Test that normalize_url adds trailing slash to plain URLs."""
    assert normalize_url("https://www.jenkins.io/doc/book") == \
        "https://www.jenkins.io/doc/book/"


def test_normalize_url_leaves_html_urls():
    """Test that normalize_url does not modify .html URLs."""
    url = "https://www.jenkins.io/doc/book/page.html"
    assert normalize_url(url) == url


def test_normalize_url_noop_if_already_slash():
    """Test that normalize_url is a no-op if URL already ends with /."""
    url = "https://www.jenkins.io/doc/book/"
    assert normalize_url(url) == url


# ── is_valid_url ─────────────────────────────────────────────────


def test_is_valid_url_accepts_valid_doc_url():
    """Test that is_valid_url accepts a valid Jenkins doc URL."""
    assert is_valid_url("https://www.jenkins.io/doc/book/pipeline/") is True


def test_is_valid_url_rejects_fragment():
    """Test that is_valid_url rejects URLs with # fragments."""
    assert is_valid_url("https://www.jenkins.io/doc/book/#section") is False


def test_is_valid_url_rejects_external_url():
    """Test that is_valid_url rejects external URLs."""
    assert is_valid_url("https://google.com/search") is False


def test_is_valid_url_rejects_non_http_scheme():
    """Test that is_valid_url rejects non-http schemes."""
    assert is_valid_url("mailto:user@jenkins.io") is False


# ── extract_page_content_container ───────────────────────────────


def test_extract_content_finds_col_8():
    """Test extraction of div.col-8 (developer docs)."""
    html = '<html><body><div class="col-8">Dev content</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = extract_page_content_container(soup)
    assert "Dev content" in result


def test_extract_content_finds_col_lg_9():
    """Test extraction of div.col-lg-9 (non-developer docs)."""
    html = '<html><body><div class="col-lg-9">User content</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = extract_page_content_container(soup)
    assert "User content" in result


def test_extract_content_falls_back_to_container():
    """Test fallback to div.container."""
    html = '<html><body><div class="container">Fallback</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = extract_page_content_container(soup)
    assert "Fallback" in result


def test_extract_content_returns_empty_on_no_match():
    """Test returns empty string when no matching div found."""
    html = '<html><body><div class="other">Nothing</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    result = extract_page_content_container(soup)
    assert result == ""


# ── Helpers for async tests ──────────────────────────────────────


def _make_mock_response(status=200, text=""):
    """Create a mock aiohttp response as an async context manager."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=text)
    return mock_resp


def _make_mock_session(responses):
    """Create a mock aiohttp session that returns responses in sequence.

    Args:
        responses: List of mock response objects to return in order.
    """
    session = MagicMock()
    call_iter = iter(responses)

    class _CtxMgr:
        def __init__(self, resp):
            self.resp = resp

        async def __aenter__(self):
            return self.resp

        async def __aexit__(self, *args):
            pass

    def get_side_effect(*args, **kwargs):
        resp = next(call_iter, responses[-1])
        return _CtxMgr(resp)

    session.get = MagicMock(side_effect=get_side_effect)
    return session


SAMPLE_HTML = """
<html><body>
<div class="col-lg-9">
    <p>Jenkins docs content</p>
    <a href="/doc/book/pipeline/">Pipeline</a>
    <a href="https://google.com">External</a>
</div>
</body></html>
"""


# ── _fetch_html ──────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_html_returns_text_on_200(mock_sleep):
    """Test _fetch_html returns HTML on successful 200 response."""
    session = _make_mock_session([_make_mock_response(200, "<html>OK</html>")])
    semaphore = asyncio.Semaphore(1)

    result = await _fetch_html(session, "https://www.jenkins.io/doc/test/", semaphore)

    assert result == "<html>OK</html>"


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_html_retries_on_429_then_succeeds(mock_sleep):
    """Test _fetch_html retries on 429 and succeeds on subsequent 200."""
    responses = [
        _make_mock_response(429),
        _make_mock_response(200, "<html>OK</html>"),
    ]
    session = _make_mock_session(responses)
    semaphore = asyncio.Semaphore(1)

    result = await _fetch_html(session, "https://www.jenkins.io/doc/test/", semaphore)

    assert result == "<html>OK</html>"
    mock_sleep.assert_called()


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_html_returns_none_on_404(mock_sleep):
    """Test _fetch_html returns None on non-retryable status like 404."""
    session = _make_mock_session([_make_mock_response(404)])
    semaphore = asyncio.Semaphore(1)

    result = await _fetch_html(session, "https://www.jenkins.io/doc/missing/", semaphore)

    assert result is None


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_html_returns_none_after_max_retries(mock_sleep):
    """Test _fetch_html gives up after exhausting retries on 500."""
    responses = [_make_mock_response(500)] * 4
    session = _make_mock_session(responses)
    semaphore = asyncio.Semaphore(1)

    result = await _fetch_html(session, "https://www.jenkins.io/doc/broken/", semaphore)

    assert result is None


# ── fetch_and_process_page ───────────────────────────────────────


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_and_process_stores_content_and_discovers_links(mock_sleep, state):
    """Test successful fetch stores content and enqueues discovered links."""
    session = _make_mock_session([_make_mock_response(200, SAMPLE_HTML)])
    semaphore = asyncio.Semaphore(1)
    queue = asyncio.Queue()
    url = "https://www.jenkins.io/doc/book/"

    await fetch_and_process_page(session, url, semaphore, queue, state)

    # Content should be stored
    assert url in state.page_content
    assert "Jenkins docs content" in state.page_content[url]

    # Should discover the valid internal link but not external
    discovered = []
    while not queue.empty():
        discovered.append(await queue.get())
    assert "https://www.jenkins.io/doc/book/pipeline/" in discovered
    assert "https://google.com" not in discovered


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_fetch_and_process_skips_on_failure(mock_sleep, state):
    """Test that failed fetch stores nothing."""
    session = _make_mock_session([_make_mock_response(404)])
    semaphore = asyncio.Semaphore(1)
    queue = asyncio.Queue()
    url = "https://www.jenkins.io/doc/missing/"

    await fetch_and_process_page(session, url, semaphore, queue, state)

    assert url not in state.page_content
    assert queue.empty()


# ── worker ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_worker_stops_on_sentinel(state):
    """Test that worker exits cleanly when receiving None sentinel."""
    session = MagicMock()
    semaphore = asyncio.Semaphore(1)
    queue = asyncio.Queue()

    await queue.put(None)
    await worker(session, semaphore, queue, state)

    assert queue.empty()


@pytest.mark.asyncio
@patch("data.collection.docs_crawler.asyncio.sleep", new_callable=AsyncMock)
async def test_worker_processes_url_then_stops(mock_sleep, state):
    """Test that worker processes a URL, then exits on sentinel."""
    session = _make_mock_session([_make_mock_response(200, SAMPLE_HTML)])
    semaphore = asyncio.Semaphore(1)
    queue = asyncio.Queue()
    url = "https://www.jenkins.io/doc/book/"

    await queue.put(url)
    await queue.put(None)
    await worker(session, semaphore, queue, state)

    assert url in state.page_content
