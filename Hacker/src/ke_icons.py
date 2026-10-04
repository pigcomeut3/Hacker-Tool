# -*- coding: utf-8 -*-
"""Generate companion .ico files for sample .ke scripts (pure Python)."""

import os
import struct

W = 256

# simple 5x7 pixel font: H, S, M
FONT = {
    "H": [
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
    "S": [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 1, 1, 1, 1],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ],
    "M": [
        [1, 0, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
    ],
}


def make_icon(letter, fg, bg_top, bg_bottom, path):
    def pixel(x, y):
        # vertical gradient background
        t = y / (W - 1)
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * t)
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * t)
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * t)
        # terminal frame
        if 24 <= x <= 232 and 20 <= y <= 236:
            if x in (24, 25, 230, 231) or y in (20, 21, 234, 235):
                return (fg[0], fg[1], fg[2], 255)
            if y <= 40:
                return (fg[0], max(0, fg[1] - 55), fg[2], 255)
            r, g, b = 6, 18, 9
            # letter glyph scaled
            glyph = FONT[letter]
            scale = 22
            gx0, gy0 = (W - 5 * scale) // 2, 62
            col = (x - gx0) // scale
            row = (y - gy0) // scale
            if 0 <= col < 5 and 0 <= row < 7 and glyph[row][col]:
                return (fg[0], fg[1], fg[2], 255)
            # cursor underscore
            if 40 <= y < 48 and 60 <= x < 196:
                return (fg[0], fg[1], fg[2], 255)
        return (r, g, b, 255)

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
    with open(path, "wb") as fh:
        fh.write(header + entry + info + xor + and_mask)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "hscripts", "icons")
    os.makedirs(outdir, exist_ok=True)
    specs = [
        ("ke_hello.ico", "H", (0, 255, 0), (4, 26, 8), (10, 70, 22)),
        ("ke_sysinfo.ico", "S", (80, 220, 255), (4, 20, 40), (14, 80, 120)),
        ("ke_matrix.ico", "M", (180, 120, 255), (24, 6, 36), (90, 30, 130)),
    ]
    for fname, letter, fg, top, bottom in specs:
        make_icon(letter, fg, top, bottom, os.path.join(outdir, fname))
        print("wrote", fname)


if __name__ == "__main__":
    main()
