"""INP / INX container I/O for Inochi2D puppets.

Container layout (all integers big-endian, see the official INP specification):

    magic        8 bytes   b"TRNSRTS\\x00"
    json length  uint32    length of the JSON payload that follows
    json         N bytes   the puppet data (UTF-8 JSON)
    b"TEX_SECT"  8 bytes
    tex count    uint32
    texture*     ...       each: uint32 payload length, uint8 encoding, payload

Texture encodings defined by the specification: 0 = PNG, 1 = TGA, 2 = BC7.

This module is deliberately dependency-free: reading and writing a puppet
container must be possible with the standard library alone, so the same code
runs inside a container, on a Windows workstation, or inside an MCP server.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

MAGIC = b"TRNSRTS\x00"
TEX_MAGIC = b"TEX_SECT"
EXT_MAGIC = b"EXT_SECT"

# uint32 -1. The official exporter writes this as the "nothing here" sentinel:
# Part.textures is a fixed-length array of texture slots and unset slots hold
# this value (the same sentinel appears as meta.thumbnailId when there is no
# thumbnail). Verified against examples/ada-static.inx, whose Part has
# textures [0, 4294967295, 4294967295].
UNSET_ID = 4294967295

# Number of texture slots a Part carries (multitexture), per the official exporter.
PART_TEXTURE_SLOTS = 3

PNG = 0
TGA = 1
BC7 = 2

ENCODING_NAMES = {PNG: "png", TGA: "tga", BC7: "bc7"}
ENCODING_IDS = {v: k for k, v in ENCODING_NAMES.items()}

_MAX_SANE = 1 << 31


class InpError(ValueError):
    """Raised when a file is not a well-formed Inochi2D container."""


@dataclass
class Texture:
    encoding: int
    data: bytes

    @property
    def encoding_name(self) -> str:
        return ENCODING_NAMES.get(self.encoding, f"unknown({self.encoding})")

    @property
    def suffix(self) -> str:
        return self.encoding_name if self.encoding in ENCODING_NAMES else "bin"


@dataclass
class Puppet:
    """A parsed puppet: the JSON payload plus the textures that came with it."""

    payload: dict[str, Any]
    textures: list[Texture] = field(default_factory=list)
    ext_sections: list[tuple[str, bytes]] = field(default_factory=list)
    source: str | None = None

    # -- convenience accessors -------------------------------------------------
    @property
    def meta(self) -> dict[str, Any]:
        return self.payload.get("meta") or {}

    @property
    def name(self) -> str:
        return str(self.meta.get("name") or "")

    @property
    def version(self) -> str:
        return str(self.meta.get("version") or "")

    @property
    def root(self) -> dict[str, Any] | None:
        node = self.payload.get("nodes")
        return node if isinstance(node, dict) else None

    @property
    def parameter_list(self) -> list[dict[str, Any]]:
        params = self.payload.get("param") or []
        return [p for p in params if isinstance(p, dict)]

    def walk(self) -> Iterable[tuple[int, dict[str, Any]]]:
        """Yield ``(depth, node)`` for every node in the puppet tree, parents first."""

        def rec(node: Any, depth: int):
            if not isinstance(node, dict):
                return
            yield depth, node
            for child in node.get("children") or []:
                yield from rec(child, depth + 1)

        if self.root:
            yield from rec(self.root, 0)

    def node_count(self) -> int:
        return sum(1 for _ in self.walk())

    def type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, node in self.walk():
            key = str(node.get("type") or "?")
            counts[key] = counts.get(key, 0) + 1
        return counts


# --------------------------------------------------------------------------- #
# reading
# --------------------------------------------------------------------------- #


def _payload_bounds(raw: bytes) -> tuple[int, int]:
    if len(raw) < 12 or raw[:8] != MAGIC:
        raise InpError("missing TRNSRTS magic; not an Inochi2D INP/INX container")
    (json_len,) = struct.unpack_from(">I", raw, 8)
    if json_len <= 0 or json_len > len(raw) - 12:
        raise InpError(f"implausible JSON length {json_len} for a {len(raw)} byte file")
    return 12, 12 + json_len


def parse(raw: bytes, *, source: str | None = None) -> Puppet:
    """Parse container bytes into a :class:`Puppet` (shared by ``load``/``loads``)."""
    start, end = _payload_bounds(raw)
    try:
        payload = json.loads(raw[start:end].decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise InpError(f"JSON payload is not valid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InpError(f"JSON payload is malformed: {exc}") from exc
    if not isinstance(payload, dict):
        raise InpError("JSON payload must be an object")

    textures: list[Texture] = []
    ext_sections: list[tuple[str, bytes]] = []
    cursor = end

    if raw[cursor:cursor + len(TEX_MAGIC)] != TEX_MAGIC:
        raise InpError(
            "missing TEX_SECT (file is truncated, or this is not an Inochi2D puppet container)"
        )
    cursor += len(TEX_MAGIC)
    if cursor + 4 > len(raw):
        raise InpError("truncated texture section header")
    (count,) = struct.unpack_from(">I", raw, cursor)
    cursor += 4
    if count > _MAX_SANE:
        raise InpError(f"implausible texture count {count}")
    for index in range(count):
        if cursor + 5 > len(raw):
            raise InpError(f"truncated texture #{index}")
        (length,) = struct.unpack_from(">I", raw, cursor)
        cursor += 4
        encoding = raw[cursor]
        cursor += 1
        if cursor + length > len(raw):
            raise InpError(f"texture #{index} overruns the file")
        textures.append(Texture(encoding=encoding, data=raw[cursor:cursor + length]))
        cursor += length

    if raw[cursor:cursor + len(EXT_MAGIC)] == EXT_MAGIC:
        cursor += len(EXT_MAGIC)
        if cursor + 4 > len(raw):
            raise InpError("truncated extension section header")
        (count,) = struct.unpack_from(">I", raw, cursor)
        cursor += 4
        for index in range(count):
            if cursor + 4 > len(raw):
                raise InpError(f"truncated extension payload #{index}")
            (name_len,) = struct.unpack_from(">I", raw, cursor)
            cursor += 4
            name = raw[cursor:cursor + name_len].decode("utf-8", "replace")
            cursor += name_len
            if cursor + 4 > len(raw):
                raise InpError("truncated extension payload length")
            (length,) = struct.unpack_from(">I", raw, cursor)
            cursor += 4
            ext_sections.append((name, raw[cursor:cursor + length]))
            cursor += length

    return Puppet(payload=payload, textures=textures, ext_sections=ext_sections, source=source)


def load(path: str | Path) -> Puppet:
    """Read a puppet from ``path`` (``.inp``, ``.inx`` — any TRNSRTS container)."""
    path = Path(path)
    return parse(path.read_bytes(), source=str(path))


def loads(raw: bytes) -> Puppet:
    """Read a puppet from bytes already in memory."""
    return parse(raw)


# --------------------------------------------------------------------------- #
# writing
# --------------------------------------------------------------------------- #


def dumps(puppet: Puppet, *, json_indent: int | None = None) -> bytes:
    """Serialise a puppet back into container bytes."""
    payload = json.dumps(
        puppet.payload,
        ensure_ascii=False,
        separators=(",", ":") if json_indent is None else None,
        indent=json_indent,
    ).encode("utf-8")

    out = bytearray()
    out += MAGIC
    out += struct.pack(">I", len(payload))
    out += payload
    out += TEX_MAGIC
    out += struct.pack(">I", len(puppet.textures))
    for texture in puppet.textures:
        out += struct.pack(">I", len(texture.data))
        out += bytes([texture.encoding])
        out += texture.data
    if puppet.ext_sections:
        out += EXT_MAGIC
        out += struct.pack(">I", len(puppet.ext_sections))
        for name, blob in puppet.ext_sections:
            encoded = name.encode("utf-8")
            out += struct.pack(">I", len(encoded))
            out += encoded
            out += struct.pack(">I", len(blob))
            out += blob
    return bytes(out)


def save(puppet: Puppet, path: str | Path, *, json_indent: int | None = None) -> Path:
    path = Path(path)
    path.write_bytes(dumps(puppet, json_indent=json_indent))
    return path


def extract_textures(puppet: Puppet, out_dir: str | Path, *, prefix: str = "texture") -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, texture in enumerate(puppet.textures):
        target = out_dir / f"{prefix}_{index}.{texture.suffix}"
        target.write_bytes(texture.data)
        written.append(target)
    return written
