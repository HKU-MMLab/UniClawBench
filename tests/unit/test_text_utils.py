from __future__ import annotations

from lib.i18n import contains_cjk


def test_contains_cjk_detects_chinese() -> None:
    assert contains_cjk("请搜索视频") is True


def test_contains_cjk_detects_mixed() -> None:
    assert contains_cjk("hello 你好 world") is True


def test_contains_cjk_rejects_pure_ascii() -> None:
    assert contains_cjk("hello world") is False


def test_contains_cjk_rejects_empty() -> None:
    assert contains_cjk("") is False


def test_contains_cjk_handles_none() -> None:
    assert contains_cjk(None) is False


def test_contains_cjk_detects_cjk_ideograph_boundary() -> None:
    # U+4E00 is the start of the CJK Unified Ideographs block
    assert contains_cjk("\u4e00") is True
    # U+9FFF is the end of the CJK Unified Ideographs block
    assert contains_cjk("\u9fff") is True


def test_contains_cjk_rejects_japanese_kana() -> None:
    # Hiragana and Katakana are not CJK Unified Ideographs
    assert contains_cjk("ひらがな") is False
    assert contains_cjk("カタカナ") is False


def test_contains_cjk_detects_kanji() -> None:
    # Kanji characters are CJK Unified Ideographs
    assert contains_cjk("漢字") is True
