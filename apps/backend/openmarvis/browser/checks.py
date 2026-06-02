from __future__ import annotations

import asyncio

HUMAN_VERIFICATION_SELECTORS = [
    'iframe[title*="reCAPTCHA"]',
    'iframe[src*="hcaptcha"]',
    'input[name*="otp"]',
    'input[name*="verification"]',
    'input[autocomplete="one-time-code"]',
    '[data-testid*="captcha"]',
    'text=请验证您是否为真人',
    'text=Verify you are human',
]


async def check_human_verification(page, *, timeout_ms: int = 3000) -> str | None:
    """Try each selector; return the first one that matches (or None).

    We probe each selector with a short timeout. The standard Playwright way
    is page.locator(sel).count() with a small wait; if the element is present
    immediately, we return it.
    """
    deadline = asyncio.get_event_loop().time() + (timeout_ms / 1000)
    while True:
        for sel in HUMAN_VERIFICATION_SELECTORS:
            try:
                count = await page.locator(sel).count()
                if count and count > 0:
                    return sel
            except Exception:  # noqa: BLE001
                pass
        if asyncio.get_event_loop().time() >= deadline:
            return None
        await asyncio.sleep(0.2)
