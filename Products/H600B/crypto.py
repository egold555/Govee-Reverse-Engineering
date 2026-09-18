"""H600B session crypto: PSK auth, then AES-ECB(16) + RC4(4).

PSK is only for e701/e702. Later frames use the 16-byte session key
from the decrypted e701 reply.
"""

from Crypto.Cipher import AES

PSK = b"MakingLifeSmarte"


def xor_stamp(plain: bytearray) -> bytearray:
    x = 0
    for b in plain[:19]:
        x ^= b
    plain[19] = x
    return plain


def rc4_apply(key: bytes, data: bytearray) -> bytearray:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = 0
    j = 0
    for n in range(len(data)):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        data[n] ^= s[(s[i] + s[j]) & 0xFF]
    return data


def encrypt_packet(plain: bytes, key: bytes) -> bytes:
    p = xor_stamp(bytearray(plain).ljust(20, b"\0")[:20])
    cipher = AES.new(key, AES.MODE_ECB)
    out = bytearray(20)
    out[:16] = cipher.encrypt(bytes(p[:16]))
    tail = rc4_apply(key, bytearray(p[16:20]))
    out[16:20] = tail
    return bytes(out)


def decrypt_packet(ct: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_ECB)
    out = bytearray(20)
    out[:16] = cipher.decrypt(bytes(ct[:16]))
    tail = rc4_apply(key, bytearray(ct[16:20]))
    out[16:20] = tail
    return bytes(out)


def pkt_auth(sub: int) -> bytes:
    p = bytearray(20)
    p[0] = 0xE7
    p[1] = sub
    return bytes(p)


def session_key_from_e701(plain: bytes) -> bytes:
    if plain[0] != 0xE7 or plain[1] != 0x01:
        raise ValueError(f"expected e701, got {plain[0]:02x}{plain[1]:02x}")
    return bytes(plain[2:18])
