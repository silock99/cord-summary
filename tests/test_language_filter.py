"""Tests for bot.language_filter module (Phase 5: LANG-01 through LANG-05)."""

import pytest

from bot import language_filter
from bot.language_filter import (
    build_language_guidelines,
    get_language_guidelines,
    load_language_config,
    load_terms,
    parse_allowlist_entry,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset module-level cache between tests."""
    language_filter._cached_guidelines = ""
    yield
    language_filter._cached_guidelines = ""


def test_load_terms_from_file(tmp_path):
    """Given a file with terms, comments, and blank lines, returns only terms."""
    f = tmp_path / "terms.txt"
    f.write_text("term1\nterm2\n# comment\n\nterm3\n", encoding="utf-8")
    result = load_terms(f)
    assert result == ["term1", "term2", "term3"]


def test_load_terms_missing_file(tmp_path):
    """Given a nonexistent path, returns empty list without raising."""
    result = load_terms(tmp_path / "nonexistent.txt")
    assert result == []


def test_parse_allowlist_entry_with_reason():
    """Given 'kill (process terminology)', returns tuple with term and reason."""
    term, reason = parse_allowlist_entry("kill (process terminology)")
    assert term == "kill"
    assert reason == "process terminology"


def test_parse_allowlist_entry_no_reason():
    """Given a plain term, returns tuple with empty reason."""
    term, reason = parse_allowlist_entry("term")
    assert term == "term"
    assert reason == ""


def test_build_language_guidelines_with_blocked():
    """Given blocked terms, returns Language Guidelines section with listed terms."""
    result = build_language_guidelines(["slur1", "slur2"], [])
    assert "## Language Guidelines" in result
    assert "- slur1" in result
    assert "- slur2" in result
    assert "variations, misspellings" in result


def test_build_language_guidelines_with_allowlist():
    """Given blocked + allowlist, returns guidelines with Exceptions section."""
    result = build_language_guidelines(["term1"], ["kill (process terminology)"])
    assert "Exceptions" in result
    assert "kill" in result
    assert "process terminology" in result


def test_build_language_guidelines_empty_blocklist():
    """Given no blocked terms, returns empty string."""
    result = build_language_guidelines([], [])
    assert result == ""


def test_load_language_config_caches_result(tmp_path):
    """After load_language_config, get_language_guidelines returns the built string."""
    blocklist = tmp_path / "blocklist.txt"
    blocklist.write_text("badword\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("# empty\n", encoding="utf-8")

    load_language_config(blocklist_path=blocklist, allowlist_path=allowlist)
    result = get_language_guidelines()
    assert "## Language Guidelines" in result
    assert "badword" in result


def test_load_language_config_missing_files_returns_empty(tmp_path):
    """With no files present, get_language_guidelines returns empty string."""
    load_language_config(
        blocklist_path=tmp_path / "nope.txt",
        allowlist_path=tmp_path / "nada.txt",
    )
    assert get_language_guidelines() == ""
