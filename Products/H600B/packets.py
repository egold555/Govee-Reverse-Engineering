"""H600B solid bulb — plaintext frames. Encrypt with crypto.encrypt_packet."""

CTRL = "00010203-0405-0607-0809-0a0b0c0d2b11"
NOTIFY = "00010203-0405-0607-0809-0a0b0c0d2b10"


def _blank() -> bytearray:
    return bytearray(20)


def power(on: bool) -> bytes:
    p = _blank()
    p[0:3] = bytes([0x33, 0x01, 1 if on else 0])
    return bytes(p)


def brightness(level: int) -> bytes:
    p = _blank()
    p[0:3] = bytes([0x33, 0x04, max(0, min(100, level))])
    return bytes(p)


def color_0d(r: int, g: int, b: int) -> bytes:
    p = _blank()
    p[0:6] = bytes([0x33, 0x05, 0x0D, r, g, b])
    return bytes(p)


def aa_query(cmd: int) -> bytes:
    p = _blank()
    p[0] = 0xAA
    p[1] = cmd
    return bytes(p)


def parse_power(pkt: bytes):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x01:
        return None
    return pkt[2] != 0


def parse_brightness(pkt: bytes):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x04:
        return None
    return pkt[2]


def parse_color(pkt: bytes):
    if len(pkt) < 6 or pkt[0] != 0xAA or pkt[1] != 0x05:
        return None
    if pkt[2] not in (0x0D, 0x02):
        return None
    return pkt[3], pkt[4], pkt[5]


def hex20(pkt: bytes) -> str:
    return " ".join(f"{b:02x}" for b in pkt)
