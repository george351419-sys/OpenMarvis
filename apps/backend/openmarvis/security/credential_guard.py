from __future__ import annotations

import re

from .policy import Decision

PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),    # Anthropic
    re.compile(r"sk-[A-Za-z0-9]{20,}"),           # OpenAI / generic sk-*
    re.compile(r"AKIA[0-9A-Z]{16}"),              # AWS access key
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),        # Google API key
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),          # GitHub PAT
    re.compile(r"xox[bpars]-[A-Za-z0-9-]{10,}"),  # Slack token
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


def redact(text: str) -> str:
    out = text
    for p in PATTERNS:
        out = p.sub("[REDACTED]", out)
    return out


class CredentialGuard:
    def scan(self, text: str) -> Decision:
        for p in PATTERNS:
            if p.search(text):
                return Decision.confirm("检测到疑似凭据，已脱敏；请确认输入安全", pattern=p.pattern)
        return Decision.allow()

    def check_text(self, text: str) -> Decision:
        for p in PATTERNS:
            if p.search(text):
                return Decision.block("credential_pattern_detected")
        return Decision.allow()

    def mask(self, text: str) -> str:
        """对凭据样式做不可逆遮罩；不抛、不删，仅替换为前缀+***。"""
        out = text
        for p in PATTERNS:
            out = p.sub(lambda m: (m.group(0)[:5] + "***") if len(m.group(0)) > 5 else "***", out)
        return out
