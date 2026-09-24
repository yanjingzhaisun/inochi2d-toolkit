"""Structural validation of Inochi2D puppets.

The validation rules here exist to close the loop that matters most for
automation: *write a puppet, read it back, prove it is still self-consistent*.
They are deliberately conservative — every rule is one that the Inochi2D
runtime depends on, not a stylistic preference.

Rules are graded so callers can tell "this file is broken" (error) from
"this file is unusual" (warning). The CLI/verify command fails only on errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .inp import PART_TEXTURE_SLOTS, Puppet, UNSET_ID

ERROR = "error"
WARNING = "warning"

# Node types known to the 0.8 puppet format (v0_8 branch of inochi2d).
KNOWN_TYPES = {
    "Node",
    "Puppet",
    "Part",
    "Mask",
    "Composite",
    "MeshGroup",
    "SimplePhysics",
    "Camera",
    "PathDeform",
}


@dataclass
class Issue:
    severity: str
    where: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - formatting helper
        return f"[{self.severity}] {self.where}: {self.message}"


def _pairs_ok(values: Any) -> bool:
    return isinstance(values, list) and len(values) % 2 == 0


def validate(puppet: Puppet) -> list[Issue]:
    """Return every structural issue found in ``puppet``."""
    issues: list[Issue] = []
    payload = puppet.payload

    for key in ("meta", "nodes"):
        if payload.get(key) is None:
            issues.append(Issue(ERROR, key, f"missing top-level '{key}' section"))

    if payload.get("meta") is not None and not isinstance(payload.get("meta"), dict):
        issues.append(Issue(ERROR, "meta", "must be an object"))

    texture_count = len(puppet.textures)
    seen_uuids: dict[int, str] = {}
    node_uuids: set[int] = set()

    depth_index = 0
    for depth, node in puppet.walk():
        depth_index += 1
        where = f"node#{depth_index} {node.get('name') or '<unnamed>'}"

        node_type = node.get("type")
        if not node_type:
            issues.append(Issue(ERROR, where, "missing 'type'"))
        elif node_type not in KNOWN_TYPES:
            issues.append(Issue(WARNING, where, f"unknown node type {node_type!r}"))

        uuid = node.get("uuid")
        if uuid is None:
            issues.append(Issue(ERROR, where, "missing 'uuid'"))
        elif not isinstance(uuid, int):
            issues.append(Issue(ERROR, where, f"uuid must be an unsigned integer, got {type(uuid).__name__}"))
        elif uuid in seen_uuids:
            issues.append(Issue(ERROR, where, f"duplicate uuid {uuid} (also used by {seen_uuids[uuid]})"))
        else:
            seen_uuids[uuid] = where
            node_uuids.add(uuid)

        transform = node.get("transform")
        if transform is None:
            issues.append(Issue(WARNING, where, "no transform"))
        elif not isinstance(transform, dict):
            issues.append(Issue(ERROR, where, "transform must be an object"))

        mesh = node.get("mesh")
        if mesh is not None:
            if not isinstance(mesh, dict):
                issues.append(Issue(ERROR, where, "mesh must be an object"))
            else:
                verts = mesh.get("verts")
                uvs = mesh.get("uvs")
                indices = mesh.get("indices")
                if not _pairs_ok(verts):
                    issues.append(Issue(ERROR, where, "'mesh.verts' must be a flat array in pairs"))
                if uvs is not None and not _pairs_ok(uvs):
                    issues.append(Issue(ERROR, where, "'mesh.uvs' must be a flat array in pairs"))
                if verts is not None and uvs is not None and len(uvs) != len(verts):
                    issues.append(
                        Issue(ERROR, where, f"mesh uv/vertex mismatch: {len(uvs)} uvs vs {len(verts)} vertex floats")
                    )
                vertex_count = (len(verts) // 2) if isinstance(verts, list) else 0
                if isinstance(indices, list):
                    bad = [i for i in indices if not isinstance(i, int) or i < 0 or i >= vertex_count]
                    if bad:
                        issues.append(
                            Issue(ERROR, where, f"{len(bad)} index/indices out of range (vertex_count={vertex_count})")
                        )
                elif indices is None:
                    issues.append(Issue(WARNING, where, "mesh without 'indices'"))

        if node_type == "Part":
            textures = node.get("textures")
            if textures is None:
                issues.append(Issue(ERROR, where, "Part without 'textures'"))
            elif not isinstance(textures, list):
                issues.append(Issue(ERROR, where, "'textures' must be an array of texture ids"))
            else:
                for tex_id in textures:
                    if tex_id == UNSET_ID:
                        continue  # empty multitexture slot, not an error
                    if not isinstance(tex_id, int) or not 0 <= tex_id < texture_count:
                        issues.append(
                            Issue(ERROR, where, f"texture id {tex_id} out of range (file has {texture_count})")
                        )
            blend_mode = node.get("blend_mode")
            if blend_mode is not None and not isinstance(blend_mode, str):
                issues.append(Issue(ERROR, where, "'blend_mode' must be a string"))
            mask_mode = node.get("mask_mode")
            if mask_mode is not None and mask_mode not in ("Mask", "Dodge"):
                issues.append(Issue(ERROR, where, f"bad mask_mode {mask_mode!r} (expected 'Mask' or 'Dodge')"))
            for masked_by in node.get("masked_by") or []:
                if not isinstance(masked_by, int):
                    issues.append(Issue(ERROR, where, "'masked_by' entries must be uuids"))

    for index, param in enumerate(puppet.parameter_list):
        where = f"param#{index} {param.get('name') or '<unnamed>'}"
        if param.get("uuid") is None:
            issues.append(Issue(ERROR, where, "missing 'uuid'"))
        points = param.get("points")
        if points is not None and not isinstance(points, list):
            issues.append(Issue(ERROR, where, "'points' must be an array"))
        for binding_index, binding in enumerate(param.get("bindings") or []):
            if not isinstance(binding, dict):
                issues.append(Issue(ERROR, f"{where} binding#{binding_index}", "must be an object"))
                continue
            bound_uuid = binding.get("uuid")
            if isinstance(bound_uuid, int) and bound_uuid not in node_uuids:
                issues.append(
                    Issue(
                        WARNING,
                        f"{where} binding#{binding_index}",
                        f"binds to uuid {bound_uuid} which is not in this puppet's node tree",
                    )
                )

    physics = payload.get("physics")
    if physics is not None:
        if not isinstance(physics, dict):
            issues.append(Issue(ERROR, "physics", "must be an object"))
        elif not physics.get("pixelsPerMeter"):
            issues.append(Issue(WARNING, "physics", "pixelsPerMeter missing or zero"))

    return issues


def summarise(puppet: Puppet) -> dict[str, Any]:
    """Machine-readable overview — the payload behind ``inochi2d inspect``."""
    return {
        "source": puppet.source,
        "name": puppet.name,
        "version": puppet.version,
        "meta": puppet.meta,
        "physics": puppet.payload.get("physics"),
        "nodes": puppet.node_count(),
        "node_types": puppet.type_counts(),
        "parameters": [
            {
                "name": p.get("name"),
                "uuid": p.get("uuid"),
                "min": p.get("min"),
                "max": p.get("max"),
                "defaults": p.get("defaults"),
                "points": len(p.get("points") or []),
                "bindings": len(p.get("bindings") or []),
            }
            for p in puppet.parameter_list
        ],
        "textures": [{"encoding": t.encoding_name, "bytes": len(t.data)} for t in puppet.textures],
        "ext_sections": [name for name, _ in puppet.ext_sections],
        "animations": len(puppet.payload.get("animations") or []),
        "automation": len(puppet.payload.get("automation") or []),
        "groups": len(puppet.payload.get("groups") or []),
    }
