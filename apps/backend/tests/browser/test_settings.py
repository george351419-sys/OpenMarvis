from openmarvis.browser.settings import BrowserSettings


def test_browser_settings_defaults():
    s = BrowserSettings()
    assert s.headless is False
    assert s.isolation_mode == "shared"
    assert s.viewport_width == 1280
    assert s.viewport_height == 800
    assert s.default_timeout_ms == 10000
    assert s.allowed_domains == []


def test_browser_settings_overrides():
    s = BrowserSettings(headless=True, isolation_mode="per_conv",
                         allowed_domains=["example.com", "github.com"])
    assert s.headless is True
    assert s.isolation_mode == "per_conv"
    assert s.allowed_domains == ["example.com", "github.com"]
