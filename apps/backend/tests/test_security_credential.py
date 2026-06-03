from openmarvis.security.credential_guard import CredentialGuard, redact


def test_redacts_anthropic_key():
    out = redact("token=sk-ant-12345678901234567890abcdefghij")
    assert "sk-ant" not in out
    assert "[REDACTED]" in out


def test_redacts_aws_access_key():
    out = redact("AKIAABCDEFGHIJKLMNOP")
    assert "AKIA" not in out


def test_guard_detects_key_returns_confirm():
    g = CredentialGuard()
    d = g.scan("set env API_KEY=sk-ant-12345678901234567890abcdefghij")
    assert d.action == "confirm"
    assert "凭据" in d.reason or "credential" in d.reason.lower()


def test_guard_clean_text_allows():
    g = CredentialGuard()
    d = g.scan("hello world")
    assert d.action == "allow"


def test_check_text_blocks_apikey():
    from openmarvis.security.credential_guard import CredentialGuard
    guard = CredentialGuard()
    d = guard.check_text("sk-ABCDE1234567890ABCDEFGHIJ")
    assert d.action == "block"


def test_check_text_allows_plain():
    from openmarvis.security.credential_guard import CredentialGuard
    guard = CredentialGuard()
    d = guard.check_text("hello world")
    assert d.action == "allow"


def test_mask_replaces_credentials():
    from openmarvis.security.credential_guard import CredentialGuard
    guard = CredentialGuard()
    key = "sk-ABCDEFGHIJKLMNOPQRSTUVWX"   # 24 chars after sk- → matches {20,}
    masked = guard.mask(f"hello {key} world")
    assert key not in masked
    assert "hello" in masked
    assert "world" in masked


def test_mask_leaves_plain_text():
    from openmarvis.security.credential_guard import CredentialGuard
    guard = CredentialGuard()
    text = "no credentials here"
    assert guard.mask(text) == text
