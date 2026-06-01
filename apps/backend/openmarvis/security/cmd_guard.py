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
    (r"\bbase64\s+-d\b", "base64 解码可能绕过审计"),
    (r">\s*/dev/sd[a-z]", "直接写入块设备"),
]


class CmdGuard:
    def check_command(self, cmd: str) -> Decision:
        for pat, reason in HIGH_RISK_PATTERNS:
            if re.search(pat, cmd):
                return Decision.block(reason=reason, pattern=pat, command=cmd)
        return Decision.allow()
