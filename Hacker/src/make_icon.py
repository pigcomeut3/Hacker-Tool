# -*- coding: utf-8 -*-
"""Generate Hacker Tool icon.ico (256x256, 32bpp) with pure Python."""

import struct
import os

W = 256

# ">" glyph (7x7)
GT = [
    [1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1],
]
# "_" glyph (7x7)
US = [[0] * 7 for _ in range(6)] + [[1] * 7]


def pixel(x, y):
    r, g, b = 3 + (x + y) // 14, 10 + (x + y) // 9, 5 + (x + y) // 16
    if 24 <= x <= 232 and 20 <= y <= 236:
        if x in (24, 25, 230, 231) or y in (20, 21, 234, 235):
            return (0, 255, 0, 255)
        if y <= 40:
            return (0, 200, 0, 255)
        r, g, b = 5, 18, 8
        scale = 12
        gx0, gy0 = 55, 95
        for gy in range(7):
            for gx in range(7):
                if GT[gy][gx] and gx0 + gx * scale <= x < gx0 + (gx + 1) * scale \
                        and gy0 + gy * scale <= y < gy0 + (gy + 1) * scale:
                    return (0, 255, 0, 255)
        ux0 = gx0 + 8 * scale
        for gy in range(7):
            for gx in range(7):
                if US[gy][gx] and ux0 + gx * scale <= x < ux0 + (gx + 1) * scale \
                        and gy0 + gy * scale <= y < gy0 + (gy + 1) * scale:
                    return (0, 255, 0, 255)
    return (min(r, 255), min(g, 255), min(b, 255), 255)


def build(path):
    rows = []
    for y in range(W - 1, -1, -1):
        for x in range(W):
            r, g, b, a = pixel(x, y)
            rows.append(bytes((b, g, r, a)))
    xor = b"".join(rows)
    and_mask = b"\x00" * (W * W // 8)
    info = struct.pack("<IiiHHIIiiII", 40, W, W * 2, 1, 32, 0, len(xor), 0, 0, 0, 0)
    size = 40 + len(xor) + len(and_mask)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, size, 22)
    header = struct.pack("<HHH", 0, 1, 1)
    with open(path, "wb") as handle:
        handle.write(header + entry + info + xor + and_mask)
    print("icon written:", path, size + 22, "bytes")


if __name__ == "__main__":
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    build(target)
