"""H6088 cube sconces — 20-byte BLE frames (plaintext).

Mask bit is at **byte 12**, not the Hexa bytes 9–10.
"""

CTRL = "00010203-0405-0607-0809-0a0b0c0d2b11"
NOTIFY = "00010203-0405-0607-0809-0a0b0c0d2b10"

CUBE_BIT = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20}


def xor20(payload19: bytes) -> bytes:
    x = 0
    for b in payload19:
        x ^= b
    return bytes(payload19) + bytes([x])


def _blank() -> bytearray:
    return bytearray(19)


def power(on: bool) -> bytes:
    p = _blank()
    p[0:3] = bytes([0x33, 0x01, 1 if on else 0])
    return xor20(p)


def brightness(level: int) -> bytes:
    p = _blank()
    p[0:3] = bytes([0x33, 0x04, max(0, min(100, level))])
    return xor20(p)


def cube_color(mask_bit: int, r: int, g: int, b: int) -> bytes:
    p = _blank()
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x01])
    p[4:7] = bytes([r, g, b])
    p[12] = mask_bit & 0xFF
    return xor20(p)


def cube_brightness(mask_bit: int, level: int) -> bytes:
    p = _blank()
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x02])
    p[4] = max(0, min(100, level))
    p[5] = mask_bit & 0xFF
    return xor20(p)


def cube_n_color(n: int, r: int, g: int, b: int) -> bytes:
    return cube_color(CUBE_BIT[n], r, g, b)


def cube_n_brightness(n: int, level: int) -> bytes:
    return cube_brightness(CUBE_BIT[n], level)


def aa_query(cmd: int, extra: bytes = b"") -> bytes:
    p = _blank()
    p[0] = 0xAA
    p[1] = cmd
    p[2 : 2 + len(extra)] = extra
    return xor20(p)


def aa_a5(page: int) -> bytes:
    return aa_query(0xA5, bytes([page]))


def parse_power(pkt: bytes):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x01:
        return None
    return pkt[2] != 0


def parse_brightness(pkt: bytes):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x04:
        return None
    return pkt[2]


def parse_a5(pkt: bytes):
    if len(pkt) < 19 or pkt[0] != 0xAA or pkt[1] != 0xA5:
        return None
    page = pkt[2]
    slots = []
    for i in range(4):
        o = 3 + i * 4
        slots.append((pkt[o], pkt[o + 1], pkt[o + 2], pkt[o + 3]))
    return page, slots


def hex20(pkt: bytes) -> str:
    return " ".join(f"{b:02x}" for b in pkt)
