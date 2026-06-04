from __future__ import annotations

import re

from .policy import Decision

HIGH_RISK_PATTERNS = [
    (r"\brm\s+-r[fF]?\b", "递归删除"),
    (r"\brm\s+-[rfFR]+\b", "递归/强制删除"),
    (r"\bmv\s+/(?!\w)", "移动根目录内容"),
    (r"\bdd\b", "块设备写入"),
    (r"\bmkfs\b", "文件系统格式化"),
    (r"\bdiskutil\s+(erase|reformat|secureErase)\b", "磁盘擦除"),
    (r"\blaunchctl\s+(remove|stop|disable|unload)\b", "操作 LaunchAgent/Daemon"),
    (r"\bkillall\b", "批量杀进程"),
    (r"\bshutdown\b", "关机/重启"),
    (r"\breboot\b", "重启"),
    (r"\bsudo\b", "提权"),
    (r":\(\)\{.*\};:", "fork bomb"),
    (r"curl\s+.*\|\s*(sh|bash|zsh)\b", "远程脚本管道执行"),
    (r"wget\s+.*\|\s*(sh|bash|zsh)\b", "远程脚本管道执行"),
    (r">\s*/dev/sd[a-z]", "直接写入块设备"),
]

# 隐蔽执行：命令通过编码绕过明文审计。命中即 block，把命令原文塞进 details。
# - base64 -d / --decode：常被用来藏 payload
# - echo $(...) | sh：command-substitution 后管道执行
# - python -c '...base64...' / perl -e '...decode...'：脚本解码后执行
# - eval $(...)：动态解释结果
ENCODING_BYPASS_PATTERNS = [
    (r"\bbase64\s+(?:-d|--decode|-D)\b", "base64 解码可能藏 payload，明文审计被绕过"),
    (r"\becho\s+[^|]*\$\([^)]*\)\s*\|\s*(?:sh|bash|zsh)\b", "echo + 命令替换 + 管道 shell 执行"),
    # python/perl -c/-e 后面任意嵌套引号都不可靠，干脆扫整段命令找危险关键词
    (r"\bpython3?\s+-c\b.*\b(?:base64|b64decode|codecs\.decode|fromhex|hex_codec)\b",
     "python -c 内嵌解码执行"),
    (r"\bperl\s+-e\b.*\bdecode(?:_base64)?\b", "perl -e 内嵌解码执行"),
    (r"\beval\s+\$\(", "eval 动态求值"),
    (r"\bxxd\s+-r\b", "xxd 反向解码可能藏 payload"),
]


class CmdGuard:
    def check_command(self, cmd: str) -> Decision:
        for pat, reason in ENCODING_BYPASS_PATTERNS:
            if re.search(pat, cmd):
                return Decision.block(
                    reason=f"encoding_bypass: {reason}",
                    pattern=pat, command=cmd,
                )
        for pat, reason in HIGH_RISK_PATTERNS:
            if re.search(pat, cmd):
                return Decision.block(reason=reason, pattern=pat, command=cmd)
        return Decision.allow()
