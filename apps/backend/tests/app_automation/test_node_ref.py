from openmarvis.app_automation.node_ref import NodeRef, encode_node_ref, parse_node_ref


def test_encode_decode_roundtrip():
    ref = NodeRef(bundle_id="com.apple.Notes", window_index=0, ax_path="0/2/1/3")
    s = encode_node_ref(ref)
    assert s == "com.apple.Notes|0|0/2/1/3"
    back = parse_node_ref(s)
    assert back == ref


def test_parse_rejects_invalid():
    import pytest
    with pytest.raises(ValueError):
        parse_node_ref("no-pipes")
    with pytest.raises(ValueError):
        parse_node_ref("a|notanint|0")
    with pytest.raises(ValueError):
        parse_node_ref("a|0|0/bad/x")


def test_ax_path_indexes():
    ref = parse_node_ref("com.apple.Notes|1|3/0/4")
    assert ref.ax_path_indexes == [3, 0, 4]
