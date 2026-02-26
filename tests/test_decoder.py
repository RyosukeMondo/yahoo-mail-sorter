"""Tests for Japanese email header decoding."""

from __future__ import annotations

from yahoo_mail_sorter.decoder import decode_header_value


class TestDecodeHeaderValue:
    def test_none_returns_empty(self) -> None:
        assert decode_header_value(None) == ""

    def test_empty_string(self) -> None:
        assert decode_header_value("") == ""

    def test_plain_ascii(self) -> None:
        assert decode_header_value("Hello World") == "Hello World"

    def test_utf8_bytes(self) -> None:
        raw = "テスト件名".encode()
        assert decode_header_value(raw) == "テスト件名"

    def test_rfc2047_utf8(self) -> None:
        raw = "=?UTF-8?B?44OG44K544OI5Lu25ZCN?="
        result = decode_header_value(raw)
        assert result == "テスト件名"

    def test_rfc2047_iso2022jp(self) -> None:
        raw = "=?ISO-2022-JP?B?GyRCJUYlOSVIN29MPhsoQg==?="
        result = decode_header_value(raw)
        assert result == "テスト件名"

    def test_whitespace_only(self) -> None:
        assert decode_header_value("   ") == ""

    def test_mixed_encoded_and_plain(self) -> None:
        raw = "=?UTF-8?B?44OG44K544OI?= test"
        result = decode_header_value(raw)
        assert "テスト" in result
        assert "test" in result
