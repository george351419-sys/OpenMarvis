from unittest.mock import AsyncMock, MagicMock

from openmarvis.browser.checks import HUMAN_VERIFICATION_SELECTORS, check_human_verification


class FakePage:
    def __init__(self, matching_selector: str | None = None):
        self.locator_calls: list[str] = []
        self._matching = matching_selector

    def locator(self, selector):
        self.locator_calls.append(selector)
        loc = MagicMock()

        async def count():
            return 1 if selector == self._matching else 0
        loc.count = AsyncMock(side_effect=count)
        return loc


async def test_check_human_verification_detects_recaptcha():
    page = FakePage(matching_selector='iframe[title*="reCAPTCHA"]')
    matched = await check_human_verification(page, timeout_ms=100)
    assert matched == 'iframe[title*="reCAPTCHA"]'


async def test_check_human_verification_returns_none_when_no_match():
    page = FakePage(matching_selector=None)
    matched = await check_human_verification(page, timeout_ms=100)
    assert matched is None


def test_selectors_list_non_empty():
    assert len(HUMAN_VERIFICATION_SELECTORS) >= 6
