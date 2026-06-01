from openmarvis.protocol.product_validator import (
    parse_card_blocks,
    validate_products,
)


def test_parse_extracts_mv_product_paths():
    text = (
        "前文\n```mv-product\n[a.md](</tmp/a.md>)\n[b.md](</tmp/b.md>)\n```\n后文"
    )
    paths = parse_card_blocks(text, "mv-product")
    assert paths == ["/tmp/a.md", "/tmp/b.md"]


def test_validate_returns_missing_paths(tmp_path):
    existing = tmp_path / "exists.md"
    existing.write_text("hi")
    text = (
        f"```mv-product\n[ok]({'<' + str(existing) + '>'})\n"
        f"[gone](</tmp/never-existed.md>)\n```"
    )
    issues = validate_products(text, written_paths={str(existing)})
    assert any("not_written" in i.kind or "missing" in i.kind for i in issues)


def test_validate_detects_overlap_with_other_card():
    text = (
        "```mv-product\n[a.md](</tmp/a.md>)\n```\n"
        "```mv-file-list\n[a.md](</tmp/a.md>)\n```"
    )
    issues = validate_products(text, written_paths={"/tmp/a.md"})
    assert any(i.kind == "overlap" for i in issues)
