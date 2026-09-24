"""The README is maintained in three languages; they must not drift apart.

Wording is translated, structure is not: section order, code blocks and the capability table have to match,
the switcher must link the other locales, and each localised file must point at the English one as canonical.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGLISH = "README.md"
LOCALES = [ENGLISH, "README.zh-CN.md", "README.ja.md"]


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _sections(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def _fence_count(text: str) -> int:
    return text.count("```") // 2


def _table_rows(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("|"))


@pytest.mark.parametrize("name", LOCALES)
def test_locale_exists_and_is_not_empty(name):
    text = _text(name)
    assert len(text) > 1000, name
    assert text.startswith("# inochi2d-toolkit")


@pytest.mark.parametrize("name", LOCALES)
def test_language_switcher_links_the_other_locales(name):
    line = _text(name).splitlines()[2]
    for other in LOCALES:
        if other == name:
            continue
        assert f"]({other})" in line, f"{name}: switcher does not link {other}"
    assert "[English](README.md)" in line or line.startswith("**English**")


def test_translations_name_english_as_canonical():
    for name in LOCALES:
        assert "canonical" in _text(name), name


def test_localised_readmes_declare_english_is_authoritative():
    for name in ("README.zh-CN.md", "README.ja.md"):
        text = _text(name)
        assert "README.md" in text
        assert "English" in text


def test_all_locales_have_the_same_number_of_sections():
    counts = {name: len(_sections(_text(name))) for name in LOCALES}
    assert len(set(counts.values())) == 1, counts


def test_bash_blocks_match_between_locales():
    """Section titles are translated, so the shared skeleton is compared by shape.

    Counts of `##` sections, fenced blocks and table rows have to agree; wording
    does not. This is what catches "a section was added to English only".
    """
    def bash_blocks(text: str) -> int:
        return sum(1 for line in text.splitlines() if line.startswith("```bash"))

    reference = bash_blocks(_text(ENGLISH))
    assert reference >= 3
    for name in LOCALES[1:]:
        assert bash_blocks(_text(name)) == reference, name


def test_section_titles_are_unique_within_each_locale():
    for name in LOCALES:
        titles = _sections(_text(name))
        assert len(titles) == len(set(titles)), f"{name} has duplicate section titles"


def test_code_blocks_and_tables_match():
    reference = (_fence_count(_text(ENGLISH)), _table_rows(_text(ENGLISH)))
    for name in LOCALES[1:]:
        assert (_fence_count(_text(name)), _table_rows(_text(name))) == reference, name


def test_capability_labels_are_translated_consistently():
    """Every locale must label capabilities with its own words, never leave English 'planned'."""
    assert "planned" in _text(ENGLISH)
    assert "计划中" in _text("README.zh-CN.md")
    assert "計画中" in _text("README.ja.md")


def test_endpoint_names_are_never_translated():
    """Command and tool names are identifiers: identical in all locales."""
    markers = ["inochi2d new out.inx --name", "inochi2d verify out.inx --warnings", "inochi_verify", "TRNSRTS"]
    for name in LOCALES:
        text = _text(name)
        for marker in markers:
            assert marker in text, f"{name} lost {marker}"


def test_no_stray_english_readme_duplicates():
    stray = [p.name for p in ROOT.glob("readme*") if p.name not in LOCALES]
    assert stray == [], f"unexpected README-like files: {stray}"


def test_relative_links_in_readmes_resolve():
    pattern = re.compile(r"\]\((?!https?://|#)([^)]+)\)")
    for name in LOCALES:
        for target in pattern.findall(_text(name)):
            assert (ROOT / target).exists(), f"{name} links to missing {target}"
