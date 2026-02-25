"""Tests for ETL description quality validation"""

from etl.description_quality import is_valid_description


def test_rejects_placeholder_description_pattern():
    assert not is_valid_description("awesome-python - technology with 0 stars")


def test_accepts_real_description():
    assert is_valid_description("Popular curated list of Python frameworks and tools")


def test_rejects_blank_description():
    assert not is_valid_description("   ")
