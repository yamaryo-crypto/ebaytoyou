"""hashing モジュールのユニットテスト。"""
import pytest
from app.match.hashing import sha256_hex


def test_same_bytes_same_hash():
    data = b"hello"
    assert sha256_hex(data) == sha256_hex(data)


def test_one_byte_difference_different_hash():
    a = b"hello"
    b = b"hellx"
    assert sha256_hex(a) != sha256_hex(b)


def test_empty_bytes():
    h = sha256_hex(b"")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
