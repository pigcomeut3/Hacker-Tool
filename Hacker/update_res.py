# -*- coding: utf-8 -*-
"""Inject Win32 icon resources (RT_ICON + RT_GROUP_ICON) into resources.dll
using the official BeginUpdateResource/UpdateResource/EndUpdateResource APIs.
The Windows kernel rebuilds the resource tree itself -> no hand-crafted PE."""
import ctypes
import os
import shutil
import struct
from ctypes import wintypes

ROOT = r"C:\Users\Xiaozhu\Desktop\Hacker"
BAK = os.path.join(ROOT, "resources.dll.bak")
DLL = os.path.join(ROOT, "resources.dll")

ICONS = [
    ("icon.ico", 100, 2),
    (r"hscripts\icons\ke_hello.ico", 101, 3),
    (r"hscripts\icons\ke_sysinfo.ico", 102, 4),
    (r"hscripts\icons\ke_matrix.ico", 103, 5),
]

RT_ICON = 3
RT_GROUP_ICON = 14
LANG = 0  # neutral


def ico_payload(path):
    raw = open(path, "rb").read()
    count = struct.unpack_from("<H", raw, 4)[0]
    return raw[6 + 16 * count:]


def group_data(payload_len, resid):
    d = struct.pack("<HHH", 0, 1, 1)
    d += struct.pack("<BBBBHHIH", 0, 0, 0, 0, 1, 32, payload_len, resid)
    return d


def main():
    shutil.copy2(BAK, DLL)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    BeginUpdateResourceW = k32.BeginUpdateResourceW
    BeginUpdateResourceW.restype = wintypes.HANDLE
    BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    UpdateResourceW = k32.UpdateResourceW
    UpdateResourceW.restype = wintypes.BOOL
    UpdateResourceW.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                ctypes.c_void_p, wintypes.WORD,
                                ctypes.c_void_p, wintypes.DWORD]
    EndUpdateResourceW = k32.EndUpdateResourceW
    EndUpdateResourceW.restype = wintypes.BOOL
    EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]

    h = BeginUpdateResourceW(DLL, False)
    if not h:
        raise OSError(ctypes.get_last_error(), "BeginUpdateResourceW failed")
    try:
        for rel, gid, iid in ICONS:
            payload = ico_payload(os.path.join(ROOT, rel))
            buf = ctypes.create_string_buffer(payload)
            ok = UpdateResourceW(h, ctypes.c_void_p(RT_ICON),
                                 ctypes.c_void_p(iid), LANG, buf, len(payload))
            if not ok:
                raise OSError(ctypes.get_last_error(), f"UpdateResource icon {iid}")
            g = group_data(len(payload), iid)
            gbuf = ctypes.create_string_buffer(g)
            ok = UpdateResourceW(h, ctypes.c_void_p(RT_GROUP_ICON),
                                 ctypes.c_void_p(gid), LANG, gbuf, len(g))
            if not ok:
                raise OSError(ctypes.get_last_error(), f"UpdateResource group {gid}")
            print(f"injected icon id={iid} group={gid} payload={len(payload)}")
    finally:
        if not EndUpdateResourceW(h, False):
            raise OSError(ctypes.get_last_error(), "EndUpdateResourceW failed")
    print("OK:", os.path.getsize(DLL), "bytes")


if __name__ == "__main__":
    main()
