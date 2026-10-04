# -*- coding: utf-8 -*-
"""Minimal ISO 9660 (Level 1) image builder, zero third-party dependencies.

Builds a bootable-less, standard data ISO from a source folder:
  system area (16 sectors) | PVD | terminator | path tables | dir records | file data
"""

import os
import re
import struct
import time

SECTOR = 2048


def _both_endian_8(value):
    """8-byte both-endian (4 LE + 4 BE)."""
    value &= 0xFFFFFFFF
    return struct.pack("<I", value) + struct.pack(">I", value)


def _both_endian_4(value):
    """4-byte both-endian (2 LE + 2 BE)."""
    value &= 0xFFFF
    return struct.pack("<H", value) + struct.pack(">H", value)


def _clean_name(raw):
    return re.sub(r"[^A-Z0-9_.\-]", "_", str(raw).upper())


def _iso_name(raw, is_dir, used):
    """8.3 Level-1 name, deduplicated via `used` set."""
    cleaned = _clean_name(raw)
    if is_dir:
        name = cleaned[:8] or "DIR"
        base = name
        n = 2
        while name in used:
            name = f"{base[:6]}_{n}"
            n += 1
        return name
    stem, dot, ext = cleaned.rpartition(".")
    stem = stem[:8] or "FILE"
    ext = ext[:3] if dot else ""
    name = f"{stem}.{ext}" if ext else stem
    base = name
    n = 2
    while name in used:
        stem_n = f"{stem[:6]}_{n}"
        name = f"{stem_n}.{ext}" if ext else stem_n
        n += 1
    return name


def _dir_record(name, location, size, is_dir, date):
    """One directory record. `name` is bytes (0x00/0x01 for . and ..)."""
    flags = 2 if is_dir else 0
    name_bytes = name if isinstance(name, bytes) else name.encode("ascii", errors="replace")
    length = 33 + len(name_bytes)
    if length % 2:
        length += 1
    record = bytearray(length)
    record[0] = length
    record[1] = 0
    record[2:10] = _both_endian_8(location)
    record[10:18] = _both_endian_8(size)
    record[18] = date[0]
    record[19] = date[1]
    record[20] = date[2]
    record[21] = date[3]
    record[22] = date[4]
    record[23] = date[5]
    record[24] = date[6]
    record[25] = flags
    record[26] = 0
    record[27] = 0
    record[28:32] = _both_endian_4(1)
    record[32] = len(name_bytes)
    record[33:33 + len(name_bytes)] = name_bytes
    return bytes(record)


def _path_table_record(name, location, parent, big_endian):
    name_bytes = name.encode("ascii", errors="replace")
    length = 8 + len(name_bytes)
    if length % 2:
        length += 1
    record = bytearray(length)
    record[0] = len(name_bytes)
    record[1] = 0
    if big_endian:
        record[2:6] = struct.pack(">I", location)
        record[6:8] = struct.pack(">H", parent)
    else:
        record[2:6] = struct.pack("<I", location)
        record[6:8] = struct.pack("<H", parent)
    record[8:8 + len(name_bytes)] = name_bytes
    return bytes(record)


def _pad(data):
    pad = SECTOR - len(data) % SECTOR
    if pad == SECTOR:
        return data
    return data + b"\x00" * pad


def build_iso(source_dir, output_path):
    """Build an ISO 9660 image of `source_dir` into `output_path`.
    Returns the total size in bytes."""
    root = os.path.abspath(source_dir)
    children = {}   # dir_abs -> [(name, is_dir, abs_path)]
    file_list = []  # (abs_path, parent_abs, name)
    used = {".": True, "..": True}

    def walk(directory):
        entries = []
        try:
            names = sorted(os.listdir(directory), key=lambda n: n.upper())
        except OSError:
            names = []
        for raw in names:
            full = os.path.join(directory, raw)
            is_dir = os.path.isdir(full)
            name = _iso_name(raw, is_dir, used)
            used[name] = True
            entries.append((name, is_dir, full))
        # ISO ordering (genisoimage-compatible): files first, then dirs
        entries.sort(key=lambda item: (item[1], item[0]))
        children[directory] = entries
        for name, is_dir, full in entries:
            if is_dir:
                walk(full)
            else:
                file_list.append((full, directory, name))

    walk(root)

    # BFS order of directories (root = 1)
    order = []
    queue = [root]
    while queue:
        current = queue.pop(0)
        order.append(current)
        for name, is_dir, full in children[current]:
            if is_dir:
                queue.append(full)
    dir_number = {d: i + 1 for i, d in enumerate(order)}
    dir_parent = {root: root}
    for d in order:
        for name, is_dir, full in children[d]:
            if is_dir:
                dir_parent[full] = d

    now = time.localtime()
    date7 = (now.tm_year - 1900, now.tm_mon, now.tm_mday,
             now.tm_hour, now.tm_min, now.tm_sec, 0)

    # ISO names for path table (must match directory records, uppercase)
    dir_iso_name = {root: ""}
    for d in order:
        for name, is_dir, full in children[d]:
            if is_dir:
                dir_iso_name[full] = name

    # Path table records (content before alignment).
    # Root record uses a 1-byte "." name like genisoimage for Windows cdfs.
    path_records = []
    for d in order:
        name = dir_iso_name[d]
        parent_num = dir_number.get(dir_parent.get(d, root), 1)
        if d == root:
            name = "\x00"
        path_records.append(_path_table_record(name, 0, parent_num, False))
    path_table_size = sum(len(rec) for rec in path_records)
    path_table_sectors = max(1, (path_table_size + SECTOR - 1) // SECTOR)

    # Compute directory record content lengths (locations not needed for size)
    dir_len = {}
    for d in order:
        content = b"".join(_dir_content(d, {}, dir_parent, children, {}, date7))
        dir_len[d] = len(content)

    # Allocate extents: system(0-15) PVD(16) term(17) LPT(18) MPT(19) dirs files
    lba = 20
    dir_extent = {}
    for d in order:
        sectors = max(1, (dir_len[d] + SECTOR - 1) // SECTOR)
        dir_extent[d] = (lba, sectors * SECTOR)
        lba += sectors
    file_extent = {}
    for full, parent, name in file_list:
        size = os.path.getsize(full)
        sectors = max(1, (size + SECTOR - 1) // SECTOR)
        file_extent[full] = (lba, size)
        lba += sectors
    total_sectors = lba

    # Build directory contents (final pass)
    dir_data = {}
    for d in order:
        content = b"".join(_dir_content(d, dir_extent, dir_parent, children, file_extent, date7))
        dir_data[d] = _pad(content)

    # Path tables with real locations
    path_records = []
    path_records_m = []
    for d in order:
        name = dir_iso_name[d]
        parent_num = dir_number.get(dir_parent.get(d, root), 1)
        location = dir_extent[d][0]
        if d == root:
            name = "\x00"
        path_records.append(_path_table_record(name, location, parent_num, False))
        path_records_m.append(_path_table_record(name, location, parent_num, True))
    path_table_l = _pad(b"".join(path_records))
    path_table_m = _pad(b"".join(path_records_m))

    # File data
    file_data = {}
    for full, parent, name in file_list:
        with open(full, "rb") as handle:
            file_data[full] = _pad(handle.read())

    # PVD
    pvd = bytearray(SECTOR)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[6] = 1
    volume_id = ("HACKER_" + os.path.basename(root))[:16].upper()
    pvd[40:72] = volume_id.encode("ascii", errors="replace").ljust(32, b" ")
    pvd[80:88] = _both_endian_8(total_sectors)
    pvd[120:124] = _both_endian_4(1)
    pvd[124:128] = _both_endian_4(1)
    pvd[128:132] = _both_endian_4(SECTOR)
    pvd[132:140] = _both_endian_8(path_table_size)
    pvd[140:144] = struct.pack("<I", 18)
    pvd[144:148] = struct.pack("<I", 0)
    pvd[148:152] = struct.pack(">I", 19)
    pvd[152:156] = struct.pack(">I", 0)
    root_loc, root_size = dir_extent[root]
    pvd[156:190] = _dir_record(b"\x00", root_loc, root_size, True, date7)
    pvd[574:702] = b"HACKER TOOL ISO BUILDER".ljust(128, b" ")
    date17 = time.strftime("%Y%m%d%H%M%S", now).encode() + b"00"
    pvd[813:830] = date17.ljust(17, b"0")
    pvd[830:847] = date17.ljust(17, b"0")
    pvd[881] = 1

    term = bytearray(SECTOR)
    term[0] = 255
    term[1:6] = b"CD001"
    term[6] = 1

    # Assemble
    out = bytearray(b"\x00" * (16 * SECTOR))
    out += pvd
    out += term
    out += path_table_l
    out += path_table_m
    for d in order:
        out += dir_data[d]
    for full, parent, name in file_list:
        out += file_data[full]
    out = out[:total_sectors * SECTOR]
    if len(out) < total_sectors * SECTOR:
        out += b"\x00" * (total_sectors * SECTOR - len(out))

    with open(output_path, "wb") as handle:
        handle.write(bytes(out))
    return len(out)


def _dir_content(d, dir_extent, dir_parent, children, file_map, date7):
    """Records of one directory: . .. subdirs files (empty maps during sizing)."""
    self_loc, self_size = dir_extent.get(d, (0, 0))
    parent = dir_parent.get(d, d)
    parent_loc, parent_size = dir_extent.get(parent, (0, 0))
    if d == parent:
        parent_loc, parent_size = self_loc, self_size
    records = [
        _dir_record(b"\x00", self_loc, self_size, True, date7),
        _dir_record(b"\x01", parent_loc, parent_size, True, date7),
    ]
    for name, is_dir, full in children.get(d, []):
        if is_dir:
            loc, size = dir_extent.get(full, (0, 0))
            records.append(_dir_record(name, loc, size, True, date7))
        else:
            loc, size = file_map.get(full, (0, 0))
            records.append(_dir_record(name + ";1", loc, size, False, date7))
    return records
