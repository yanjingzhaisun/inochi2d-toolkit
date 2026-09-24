"""Constructing Inochi2D puppets from scratch.

Everything here writes the *documented* 0.8 payload shape. The reference for
"what a minimal puppet looks like" is the official sample shipped in the
inochi2d repository (``examples/empty08.inx``, 702 bytes) — see
``tools/fetch_examples.py``. Keep this module in sync with that file rather
than with the (self-described "out of date") wiki.

Rigging helpers (mesh generation, deformers, physics, jelly-eye) live in
``rig.py`` and are being built out; nothing in this module assumes them.
"""

from __future__ import annotations

import random
from typing import Any, Iterable

from .inp import PART_TEXTURE_SLOTS, Puppet, UNSET_ID

VERSION = "v0.8.6"  # the format version Creator 0.8.6 writes; NOT this toolkit's version
NO_THUMBNAIL = 4294967295  # uint32 -1, as written by the official exporter


def new_uuid(seed: random.Random | None = None) -> int:
    """Allocate a uuid in the same range the official exporter uses (uint32)."""
    rng = seed or random.Random()
    uuid = rng.getrandbits(32)
    return uuid or 1


def minimal_payload(name: str = "New Puppet", *, seed: random.Random | None = None) -> dict[str, Any]:
    """A payload structurally identical to the official empty 0.8 puppet.

    The official `examples/empty08.inx` contains a Root node with exactly one
    empty child, so we reproduce that shape rather than an empty root — the
    byte-for-byte regression test depends on it.
    """
    rng = seed or random.Random()
    return {
        "meta": {
            "name": name,
            "version": VERSION,
            "rigger": "",
            "artist": "",
            "rights": None,
            "copyright": "",
            "licenseURL": "",
            "contact": "",
            "reference": "",
            "thumbnailId": NO_THUMBNAIL,
            "preservePixels": False,
        },
        "physics": {"pixelsPerMeter": 1000.0, "gravity": 9.8},
        "nodes": {
            "uuid": new_uuid(rng),
            "name": "Root",
            "type": "Node",
            "enabled": True,
            "zsort": 0.0,
            "transform": {"trans": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0], "scale": [1.0, 1.0]},
            "lockToRoot": False,
            "children": [node("Node", uuid=new_uuid(rng))],
        },
        "param": None,
        "automation": None,
        "animations": None,
        "groups": [],
    }


def minimal_puppet(name: str = "New Puppet", *, seed: random.Random | None = None) -> Puppet:
    return Puppet(payload=minimal_payload(name, seed=seed))


def node(
    name: str,
    *,
    type: str = "Node",  # noqa: A002 - matches the format's field name
    uuid: int | None = None,
    zsort: float = 0.0,
    transform: dict[str, Any] | None = None,
    children: Iterable[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a node dict with the fields the format requires, plus any extras."""
    entry: dict[str, Any] = {
        "uuid": uuid if uuid is not None else new_uuid(),
        "name": name,
        "type": type,
        "enabled": True,
        "zsort": zsort,
        "transform": transform
        or {"trans": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0], "scale": [1.0, 1.0]},
        "lockToRoot": False,
    }
    if children is not None:
        entry["children"] = list(children)
    entry.update(extra)
    return entry


def append_child(parent: dict[str, Any], child: dict[str, Any]) -> None:
    parent.setdefault("children", []).append(child)


def mesh(
    verts: list[float],
    uvs: list[float],
    indices: list[int],
    *,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Mesh data as the official exporter writes it (flat arrays, pairs of two)."""
    if len(verts) % 2 or len(uvs) % 2:
        raise ValueError("verts and uvs must be flat arrays in pairs")
    if len(uvs) != len(verts):
        raise ValueError("verts and uvs must have the same length")
    vertex_count = len(verts) // 2
    if any(not isinstance(i, int) or i < 0 or i >= vertex_count for i in indices):
        raise ValueError("indices must reference existing vertices")
    return {"verts": list(verts), "uvs": list(uvs), "indices": list(indices), "origin": list(origin)}


def texture_slots(texture_ids: Iterable[int]) -> list[int]:
    """Pad a Part's texture ids to the fixed slot count the format uses.

    Verified against the official textured sample, where a one-texture Part
    carries ``[0, 4294967295, 4294967295]``.
    """
    slots = list(texture_ids)
    if len(slots) > PART_TEXTURE_SLOTS:
        raise ValueError(f"a Part carries at most {PART_TEXTURE_SLOTS} texture slots, got {len(slots)}")
    return slots + [UNSET_ID] * (PART_TEXTURE_SLOTS - len(slots))


def part(
    name: str,
    *,
    texture_ids: Iterable[int],
    mesh_data: dict[str, Any],
    uuid: int | None = None,
    zsort: float = 0.0,
    opacity: float = 1.0,
    blend_mode: str = "Normal",
    **extra: Any,
) -> dict[str, Any]:
    """A Part node with the field set the official exporter writes."""
    node_ = node(
        name,
        type="Part",
        uuid=uuid,
        zsort=zsort,
        mesh=mesh_data,
        textures=texture_slots(texture_ids),
        blend_mode=blend_mode,
        tint=[1.0, 1.0, 1.0],
        screenTint=[0.0, 0.0, 0.0],
        emissionStrength=1.0,
        mask_threshold=0.5,
        opacity=opacity,
        **extra,
    )
    return node_
