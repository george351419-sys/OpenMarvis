from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

CardType = Literal[
    "mv-file-list",
    "mv-image-gallery",
    "mv-video-card",
    "mv-delete-list",
    "mv-product",
    "mv-tool-call",
    "mv-app-list",
    "mv-ask-user",
]

CARD_TYPES = SimpleNamespace(
    FILE_LIST="mv-file-list",
    IMAGE_GALLERY="mv-image-gallery",
    VIDEO="mv-video-card",
    DELETE_LIST="mv-delete-list",
    PRODUCT="mv-product",
    TOOL_CALL="mv-tool-call",
    APP_LIST="mv-app-list",
    ASK_USER="mv-ask-user",
)
