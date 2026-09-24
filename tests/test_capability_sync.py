"""Capability metadata must agree everywhere it is stated.

`CAPABILITIES` in `cli.py` is the source of truth; the README tables (all three languages), the roadmap and
`inochi2d doctor` all restate it. Restating is fine, drifting is not — and the README makes a promise that is
checkable: the implemented commands need nothing external, so a fresh clone runs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inochi2d_toolkit.cli import CAPABILITIES, REQUIREMENTS, doctor_report  # noqa: E402

LOCALES = ["README.md", "README.zh-CN.md", "README.ja.md"]
ROW = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|\s*([^|]+?)\s*\|", re.MULTILINE)


def _capability_table(path: str) -> dict[str, str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    return {name: status for name, status in ROW.findall(text) if name in CAPABILITIES}


def test_every_locale_lists_the_same_capabilities_in_the_same_order():
    for path in LOCALES:
        assert list(_capability_table(path)) == list(CAPABILITIES), path


def test_english_readme_status_matches_the_code():
    table = _capability_table("README.md")
    for name, (status, _) in CAPABILITIES.items():
        assert table[name] == status, name


def test_roadmap_mentions_every_capability():
    """Capabilities may appear as `` `name` ``, `` `inochi2d name` `` or `` `name/` ``.

    Collected as tokens rather than matched as substrings: substring tests pass by accident (`` `bridge/` ``
    contains `` `bridge`` but not `` `bridge` ``), and they would let a real omission through.
    """
    roadmap = (ROOT / "docs/roadmap.md").read_text(encoding="utf-8")
    tokens: set[str] = set()
    for raw in re.findall(r"`([^`]+)`", roadmap):
        for word in re.split(r"[\s,]+", raw.strip()):
            tokens.add(word.strip("/"))
    for name in CAPABILITIES:
        assert name in tokens, f"roadmap does not mention {name} (tokens: {sorted(tokens)})"


def test_requirements_cover_exactly_the_capabilities():
    assert set(REQUIREMENTS) == set(CAPABILITIES)


def test_implemented_capabilities_require_nothing_external():
    """The README's promise — a fresh clone runs the implemented commands with stdlib only."""
    for name, (status, _) in CAPABILITIES.items():
        if status == "implemented":
            assert REQUIREMENTS[name] == (), f"{name} is implemented but declares requirements"


def test_doctor_agrees_with_the_capability_table():
    report = doctor_report()
    entries = report["capabilities"]
    assert [entry["capability"] for entry in entries] == list(CAPABILITIES)
    for entry in entries:
        name = entry["capability"]
        assert entry["status"] == CAPABILITIES[name][0], name
        assert entry["needs"] == list(REQUIREMENTS[name]), name
        assert entry["ready"] == (not entry["blocked_by"]), name


def test_doctor_covers_every_requirement_it_can_see():
    """A capability must never be blocked by a requirement that is not itself checked."""
    checked = {entry["check"] for entry in doctor_report()["checks"]}
    for needs in REQUIREMENTS.values():
        for need in needs:
            assert need in checked, f"{need} is a requirement but doctor never checks it"


def test_doctor_report_is_json_serialisable():
    json.loads(json.dumps(doctor_report()))
