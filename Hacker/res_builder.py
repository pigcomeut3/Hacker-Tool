# -*- coding: utf-8 -*-
"""Build a Win32 .res file embedding all Hacker icons (RT_ICON + RT_GROUP_ICON),
so Windows dialogs (Change Icon...) can see them inside resources.dll."""

import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))

RT_ICON = 3
RT_GROUP_ICON = 14
LANG_EN_US = 0x0409
MEM_FLAGS = 0x1030

ICON_FILES = [
    ("icon.ico", 100, 1),
    ("hscripts/icons/ke_hello.ico", 101, 2),
    ("hscripts/icons/ke_sysinfo.ico", 102, 3),
    ("hscripts/icons/ke_matrix.ico", 103, 4),
]


def read_ico(path):
    data = open(path, "rb").read()
    if data[:4] != b"\x00\x00\x01\x00":
        raise ValueError(f"not an ICO file: {path}")
    count = struct.unpack_from("<H", data, 4)[0]
    entries = []
    for i in range(count):
        w, h, colors, res, planes, bitcount, size, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + i * 16
        )
        entries.append(
            {
                "w": w or 256,
                "h": h or 256,
                "colors": colors,
                "planes": planes,
                "bitcount": bitcount,
                "size": size,
                "offset": offset,
                "data": data[offset:offset + size],
            }
        )
    return entries


def align4(buf):
    while len(buf) % 4:
        buf += b"\x00"
    return buf


def res_record(restype, resid, payload):
    """One .res record (integer type/name ids, no strings)."""
    header = struct.pack(
        "<IIHHIHHII",
        len(payload),          # DataSize
        0x20,                  # HeaderSize
        restype,               # Type (WORD id)
        resid,                 # Name (WORD id)
        0,                     # DataVersion
        MEM_FLAGS,             # MemoryFlags
        LANG_EN_US,            # LanguageId
        0,                     # Version
        0,                     # Characteristics
    )
    # header is 28 bytes; pad 4 so data starts on a 4-byte boundary
    assert len(header) == 28
    return header + b"\x00" * 4 + align4(payload)


def build_res(out_path):
    records = b""
    icon_id = 1
    group_id = 200
    group_payloads = []

    for rel, group_res_id, order in ICON_FILES:
        frames = read_ico(os.path.join(ROOT, rel))
        grp_entries = b""
        for frame in frames:
            records += res_record(RT_ICON, icon_id, frame["data"])
            grp_entries += struct.pack(
                "<BBBBHHIH",
                frame["w"] & 0xFF,
                frame["h"] & 0xFF,
                frame["colors"],
                0,
                frame["planes"],
                frame["bitcount"],
                len(frame["data"]),
                icon_id,
            )
            icon_id += 1
        new_header = struct.pack("<HHH", 0, 1, len(frames))
        group_payloads.append((group_res_id, new_header + grp_entries))
        group_id += 1

    # groups appended after all icon images
    for group_res_id, payload in group_payloads:
        records += res_record(RT_GROUP_ICON, group_res_id, payload)

    with open(out_path, "wb") as fh:
        fh.write(records)
    print(f"wrote {out_path} ({len(records)} bytes, "
          f"{sum(1 for _ in ICON_FILES)} icon groups, {icon_id - 1} images)")


if __name__ == "__main__":
    build_res(os.path.join(ROOT, "resources.res"))
