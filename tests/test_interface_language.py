"""Everything that crosses an interface is English.

The project speaks English at every boundary a caller can see: CLI stdout/stderr and `--help` text, MCP tool
names and descriptions, exception messages, log lines, and the source comments that carry the reasoning.
Localisation is a documentation concern only — `README.zh-CN.md` and `README.ja.md` are the two translated
files, and they are checked by `test_readmes.py`, not here.

Why a test instead of a convention: a Chinese sentence printed by `inochi2d status` survived review once. It
is a one-line mistake that no reader of the English docs would notice, so the check has to be mechanical.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# CJK ideographs, kana and full-width punctuation — the failure mode this guards against.
CJK = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")

# Non-ASCII characters that are typography, not language: allowed in interface strings.
ALLOWED_NON_ASCII = set("—–…→←×·±≥≤°§«»“”‘’\u00a0")

# Translated documentation is exempt on purpose; see the module docstring.
EXEMPT = {"README.zh-CN.md", "README.ja.md", "tests/test_readmes.py", "tests/test_interface_language.py"}


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [name for name in out.split() if name not in EXEMPT]


def _code_files() -> list[str]:
    return [name for name in _tracked_files() if name.startswith(("src/", "tools/"))]


@pytest.mark.parametrize("name", _code_files())
def test_code_contains_no_cjk(name):
    offenders = [
        (number, line.strip())
        for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), start=1)
        if CJK.search(line)
    ]
    assert offenders == [], f"{name} has non-English text: {offenders[:5]}"


@pytest.mark.parametrize("name", _code_files())
def test_non_ascii_in_code_is_only_typography(name):
    for number, line in enumerate((ROOT / name).read_text(encoding="utf-8").splitlines(), start=1):
        for char in line:
            if ord(char) > 127:
                assert char in ALLOWED_NON_ASCII, f"{name}:{number} has unexpected character {char!r}"


def test_docs_and_metadata_are_english():
    """Internal docs are English; only the localised READMEs are translated."""
    for name in _tracked_files():
        if not (name.startswith("docs/") or name in {"AGENTS.md", "LICENSE", "pyproject.toml"}):
            continue
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not CJK.search(text), f"{name} is not English"


def test_every_tracked_text_file_is_utf8_and_decodable():
    for name in _tracked_files():
        if name.endswith((".png", ".inx", ".inp", ".tga", ".jpg")):
            continue
        (ROOT / name).read_text(encoding="utf-8")


def test_mcp_tool_names_and_descriptions_are_english_and_stable():
    """MCP names are identifiers agents call: ASCII snake_case, described in English."""
    source = (ROOT / "src/inochi2d_toolkit/mcp_server.py").read_text(encoding="utf-8")
    names = re.findall(r"\ndef\s+([a-z_][a-z0-9_]*)\s*\(", source)
    assert names, "no tool functions found"
    for name in names:
        if name.startswith("_"):
            continue
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name), name
        assert name.startswith("inochi_"), f"{name} should carry the inochi_ prefix"
        assert not CJK.search(name)


def test_cli_help_strings_are_english():
    source = (ROOT / "src/inochi2d_toolkit/cli.py").read_text(encoding="utf-8")
    for literal in re.findall(r'help\s*=\s*"([^"]*)"', source):
        assert literal.strip(), "empty help string"
        assert not CJK.search(literal), literal


def test_exception_messages_are_english():
    for name in _code_files():
        source = (ROOT / name).read_text(encoding="utf-8")
        for message in re.findall(r"(?:raise|InpError|Issue)\([^)]*?[\"']([^\"']{3,})[\"']", source):
            assert not CJK.search(message), f"{name}: {message}"


def test_commit_messages_are_english():
    """The history is part of the interface: no CJK in any commit subject in this repository."""
    log = subprocess.run(
        ["git", "log", "--pretty=%s%n%b"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    offenders = [line for line in log.splitlines() if CJK.search(line)]
    assert offenders == [], offenders[:5]
