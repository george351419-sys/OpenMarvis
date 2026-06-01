from openmarvis.protocol.cards import CARD_TYPES
from openmarvis.protocol.events import SSE_EVENTS, SSEEvent


def test_card_types_match_frontend_strings():
    assert CARD_TYPES.PRODUCT == "mv-product"
    assert CARD_TYPES.FILE_LIST == "mv-file-list"
    assert CARD_TYPES.ASK_USER == "mv-ask-user"


def test_sse_event_enum_string_values():
    assert SSE_EVENTS.CONTENT_DELTA == "content_delta"
    assert SSE_EVENTS.TOOL_CALL_START == "tool_call_start"
    assert SSE_EVENTS.DONE == "done"


def test_sseevent_to_dict():
    ev = SSEEvent(event=SSE_EVENTS.CONTENT_DELTA, data={"text": "hi"})
    d = ev.to_dict()
    assert d["event"] == "content_delta"
    assert d["data"] == '{"text": "hi"}'
