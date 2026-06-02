from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings


@pytest.fixture
def fake_playwright(monkeypatch):
    """Patch async_playwright().start() to return a controllable stub."""
    playwright_obj = MagicMock()
    chromium = MagicMock()
    playwright_obj.chromium = chromium
    chromium.launch_persistent_context = AsyncMock(return_value=MagicMock(
        new_page=AsyncMock(return_value=MagicMock()),
        close=AsyncMock(),
    ))

    start = AsyncMock(return_value=playwright_obj)
    monkeypatch.setattr("openmarvis.browser.pool.async_playwright",
                        lambda: MagicMock(start=start))
    return playwright_obj


async def test_pool_lazy_starts_playwright(tmp_path, fake_playwright):
    pool = BrowserPool(settings=BrowserSettings(),
                       profile_dir_base=tmp_path / "profile-base")
    assert not pool.is_started()
    page = await pool.get_page(conv_id="c1")
    assert page is not None
    assert pool.is_started()


async def test_shared_mode_reuses_context(tmp_path, fake_playwright):
    pool = BrowserPool(settings=BrowserSettings(isolation_mode="shared"),
                       profile_dir_base=tmp_path / "profile-base")
    await pool.get_page(conv_id="c1")
    await pool.get_page(conv_id="c2")
    assert fake_playwright.chromium.launch_persistent_context.call_count == 1


async def test_per_conv_mode_separate_contexts(tmp_path, fake_playwright):
    pool = BrowserPool(settings=BrowserSettings(isolation_mode="per_conv"),
                       profile_dir_base=tmp_path / "profile-base")
    await pool.get_page(conv_id="c1")
    await pool.get_page(conv_id="c2")
    assert fake_playwright.chromium.launch_persistent_context.call_count == 2


async def test_shutdown_closes_all_contexts(tmp_path, fake_playwright):
    pool = BrowserPool(settings=BrowserSettings(),
                       profile_dir_base=tmp_path / "profile-base")
    await pool.get_page(conv_id="c1")
    await pool.shutdown()
    assert not pool.is_started()
