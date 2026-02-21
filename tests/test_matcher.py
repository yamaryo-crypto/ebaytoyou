"""matcher モジュールのユニットテスト。"""
import pytest
from app.match.matcher import check_match, MatchResult


def test_sha256_match_returns_true():
    result = check_match("abc", "abc", also_accept_same_image_url=False)
    assert result.match is True
    assert result.evidence == "sha256"


def test_sha256_mismatch_returns_false():
    result = check_match("abc", "def", also_accept_same_image_url=False)
    assert result.match is False
    assert result.evidence == ""


def test_url_match_when_also_accept_same_image_url():
    result = check_match(
        "x", "y",
        our_image_url="https://same.com/1.jpg",
        their_image_url="https://same.com/1.jpg",
        also_accept_same_image_url=True,
    )
    assert result.match is True
    assert result.evidence == "url"


def test_url_mismatch_no_match():
    result = check_match(
        "x", "y",
        our_image_url="https://a.com/1.jpg",
        their_image_url="https://b.com/2.jpg",
        also_accept_same_image_url=True,
    )
    assert result.match is False


def test_both_sha256_and_url_match_evidence_both():
    result = check_match(
        "same", "same",
        our_image_url="https://same.com/1.jpg",
        their_image_url="https://same.com/1.jpg",
        also_accept_same_image_url=True,
    )
    assert result.match is True
    assert result.evidence == "both"
