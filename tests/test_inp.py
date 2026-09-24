"""Container I/O and validation tests.

The regression corpus is the pair of official samples in the inochi2d repo
(``examples/empty08.inx`` = 702 B minimal puppet, ``examples/ada-static.inx`` =
7.1 MB single-part puppet with a texture). Fetch them with
``python tools/fetch_examples.py``; tests that need them skip when absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from inochi2d_toolkit import build, inp, puppet

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EMPTY08 = EXAMPLES / "empty08.inx"
ADA = EXAMPLES / "ada-static.inx"


def _roundtrip(path: Path) -> tuple[inp.Puppet, inp.Puppet]:
    original = inp.load(path)
    return original, inp.parse(inp.dumps(original))


def test_minimal_puppet_roundtrip():
    doc = build.minimal_puppet("Round Trip")
    again = inp.parse(inp.dumps(doc))
    assert again.payload == doc.payload
    assert puppet.validate(doc) == []
    assert again.node_count() == 2  # Root + the empty child the format expects


def test_minimal_puppet_starts_with_magic_and_big_endian_length():
    raw = inp.dumps(build.minimal_puppet("Magic"))
    assert raw[:8] == b"TRNSRTS\x00"
    assert int.from_bytes(raw[8:12], "big") > 0
    assert b"TEX_SECT" in raw


@pytest.mark.skipif(not EMPTY08.exists(), reason="run tools/fetch_examples.py first")
def test_official_empty_sample_is_reproducible_byte_for_byte():
    original = EMPTY08.read_bytes()
    doc = inp.load(EMPTY08)
    assert len(original) == 702
    assert inp.dumps(doc) == original, "re-serialising the official sample must reproduce its bytes"


@pytest.mark.skipif(not EMPTY08.exists(), reason="run tools/fetch_examples.py first")
def test_official_empty_sample_payload():
    doc = inp.load(EMPTY08)
    assert doc.version == "v0.8.6"
    assert doc.node_count() == 2
    assert doc.textures == []
    assert puppet.validate(doc) == []
    assert set(doc.payload) == {
        "meta",
        "physics",
        "nodes",
        "param",
        "automation",
        "animations",
        "groups",
    }


@pytest.mark.skipif(not ADA.exists(), reason="run tools/fetch_examples.py first")
def test_official_textured_sample_roundtrip():
    original, again = _roundtrip(ADA)
    assert again.payload == original.payload
    assert len(original.textures) >= 1
    assert [t.data for t in again.textures] == [t.data for t in original.textures]
    assert original.textures[0].encoding_name in {"png", "tga", "bc7"}


@pytest.mark.skipif(not ADA.exists(), reason="run tools/fetch_examples.py first")
def test_official_textured_sample_passes_validation():
    """The official exporter's own output must be clean — no false positives."""
    doc = inp.load(ADA)
    issues = puppet.validate(doc)
    assert [str(i) for i in issues] == []


@pytest.mark.skipif(not ADA.exists(), reason="run tools/fetch_examples.py first")
def test_empty_multitexture_slots_are_a_sentinel_not_an_error():
    doc = inp.load(ADA)
    part_node = next(n for _, n in doc.walk() if n.get("type") == "Part")
    assert part_node["textures"][1:] == [inp.UNSET_ID] * (len(part_node["textures"]) - 1)
    assert not any("out of range" in str(i) for i in puppet.validate(doc))


def test_texture_slots_are_padded_to_the_fixed_count():
    assert build.texture_slots([0]) == [0, inp.UNSET_ID, inp.UNSET_ID]
    assert build.texture_slots([]) == [inp.UNSET_ID] * inp.PART_TEXTURE_SLOTS
    with pytest.raises(ValueError):
        build.texture_slots([0, 1, 2, 3])


def test_part_helper_matches_official_field_set():
    node = build.part(
        "ada-chan.png",
        texture_ids=[0],
        mesh_data=build.mesh([-1.0, -2.0, -1.0, 2.0, 1.0, -2.0, 1.0, 2.0], [0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0], [0, 1, 2, 2, 1, 3]),
    )
    for field in (
        "uuid",
        "name",
        "type",
        "enabled",
        "zsort",
        "transform",
        "lockToRoot",
        "mesh",
        "textures",
        "blend_mode",
        "tint",
        "screenTint",
        "emissionStrength",
        "mask_threshold",
        "opacity",
    ):
        assert field in node, field
    assert node["type"] == "Part"
    assert node["mesh"]["origin"] == [0.0, 0.0]


def test_mesh_helper_rejects_inconsistent_input():
    with pytest.raises(ValueError):
        build.mesh([0.0, 0.0], [0.0, 0.0, 1.0, 1.0], [])
    with pytest.raises(ValueError):
        build.mesh([0.0, 0.0, 1.0, 1.0], [0.0, 0.0, 1.0, 1.0], [0, 9])


def test_container_without_texture_section_is_rejected():
    raw = bytearray(inp.dumps(build.minimal_puppet("NoTex")))
    marker = raw.index(b"TEX_SECT")
    with pytest.raises(inp.InpError):
        inp.parse(bytes(raw[:marker]))


def test_validator_catches_duplicate_uuid():
    doc = build.minimal_puppet("Dup")
    doc.root["children"] = [build.node("a", uuid=7), build.node("b", uuid=7)]
    issues = puppet.validate(doc)
    assert any("duplicate uuid" in str(i) for i in issues)


def test_validator_catches_texture_index_out_of_range():
    doc = build.minimal_puppet("Tex")
    doc.root["children"] = [
        build.node("part", type="Part", textures=[0], mesh={"verts": [0.0, 0.0], "uvs": [0.0, 0.0], "indices": []})
    ]
    issues = puppet.validate(doc)
    assert any("out of range" in str(i) for i in issues)


def test_validator_catches_uv_vertex_mismatch():
    doc = build.minimal_puppet("Mesh")
    doc.root["children"] = [
        build.node(
            "bad-mesh",
            mesh={"verts": [0.0, 0.0, 1.0, 1.0], "uvs": [0.0, 0.0], "indices": [0, 1]},
        )
    ]
    issues = puppet.validate(doc)
    assert any("uv/vertex mismatch" in str(i) for i in issues)


def test_validator_catches_index_out_of_range():
    doc = build.minimal_puppet("Idx")
    doc.root["children"] = [
        build.node("bad-index", mesh={"verts": [0.0, 0.0, 1.0, 1.0], "uvs": [0.0, 0.0, 1.0, 1.0], "indices": [0, 5]})
    ]
    issues = puppet.validate(doc)
    assert any("out of range" in str(i) for i in issues)


def test_inp_rejects_non_container():
    with pytest.raises(inp.InpError):
        inp.parse(b"not an inochi puppet")


def test_inp_rejects_truncated_texture_section():
    raw = inp.dumps(build.minimal_puppet("Trunc"))[:-6]
    with pytest.raises(inp.InpError):
        inp.parse(raw)


def test_summary_is_json_serialisable():
    doc = build.minimal_puppet("Summary")
    assert json.loads(json.dumps(puppet.summarise(doc)))["nodes"] == 2
