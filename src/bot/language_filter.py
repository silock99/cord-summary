"""Language filter: load blocklist/allowlist and build prompt guidelines (Phase 5)."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_cached_guidelines: str = ""


def load_terms(filepath: Path) -> list[str]:
    """Load terms from a text file, one per line.

    Skips blank lines and lines starting with #.
    Returns empty list if file does not exist.
    """
    if not filepath.exists():
        logger.warning(f"Language file not found: {filepath}")
        return []

    text = filepath.read_text(encoding="utf-8")
    terms: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        terms.append(stripped)
    return terms


def parse_allowlist_entry(entry: str) -> tuple[str, str]:
    """Parse an allowlist entry into (term, reason).

    Format: "term (reason for allowing)" or just "term".
    """
    entry = entry.strip()
    if "(" in entry and entry.endswith(")"):
        idx = entry.index("(")
        term = entry[:idx].strip()
        reason = entry[idx + 1 : -1].strip()
        return (term, reason)
    return (entry, "")


def build_language_guidelines(blocked: list[str], allowed: list[str]) -> str:
    """Build the Language Guidelines prompt section.

    Returns empty string if no blocked terms are configured.
    """
    if not blocked:
        return ""

    parts: list[str] = []
    parts.append("\n\n## Language Guidelines\n")
    parts.append(
        "When writing your summary, do NOT use any of the following terms or "
        "phrases. Also avoid obvious variations, misspellings, abbreviations, "
        "and leetspeak substitutions of these terms:\n"
    )
    for term in blocked:
        parts.append(f"- {term}")

    if allowed:
        parts.append("\nExceptions:")
        for entry in allowed:
            term, reason = parse_allowlist_entry(entry)
            if reason:
                parts.append(f'- "{term}" (acceptable because: {reason})')
            else:
                parts.append(f'- "{term}"')

    parts.append(
        "\nIf a discussion topic involved blocked language, summarize the "
        "topic's substance without using the blocked terms themselves."
    )

    return "\n".join(parts)


def load_language_config(
    blocklist_path: Path | None = None,
    allowlist_path: Path | None = None,
) -> None:
    """Load language config from files and cache the guidelines string.

    Defaults to blocklist.txt and allowlist.txt in project root.
    """
    global _cached_guidelines

    if blocklist_path is None:
        blocklist_path = Path("blocklist.txt")
    if allowlist_path is None:
        allowlist_path = Path("allowlist.txt")

    blocked = load_terms(blocklist_path)
    allowed = load_terms(allowlist_path)

    _cached_guidelines = build_language_guidelines(blocked, allowed)

    if _cached_guidelines:
        token_estimate = len(_cached_guidelines) // 4
        logger.info(
            f"Language guidelines loaded: {len(blocked)} blocked, "
            f"{len(allowed)} allowed (~{token_estimate} tokens)"
        )
        if token_estimate > 200:
            logger.warning(
                f"Language guidelines section is large (~{token_estimate} tokens). "
                "Consider reducing blocklist size."
            )
    else:
        logger.info("No language guidelines configured (empty blocklist)")


def get_language_guidelines() -> str:
    """Return the cached language guidelines string."""
    return _cached_guidelines
