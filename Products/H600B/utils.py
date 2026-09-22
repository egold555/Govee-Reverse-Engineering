import asyncio
import logging
from bleak import BleakScanner
from Crypto.Cipher import AES

SEND_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
RECV_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

# Auth only. Session key comes from the decrypted e701 reply.
PSK = b"MakingLifeSmarte"

logger = logging.getLogger(__name__)


async def find_device(name):
    devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
    for _, (device, adv_data) in devices.items():
        if adv_data.local_name and name in adv_data.local_name:
            return (device, adv_data)
    return (None, None)


def compute_xor(ba):
    res = 0
    for b in ba:
        res = res ^ b
    return res


def rc4_apply(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = 0
    j = 0
    out = bytearray(data)
    for n in range(len(out)):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out[n] ^= s[(s[i] + s[j]) & 0xFF]
    return out


def encrypt_packet(plain, key):
    p = bytearray(plain).ljust(20, b"\0")[:20]
    p[19] = compute_xor(p[:19])
    cipher = AES.new(key, AES.MODE_ECB)
    out = bytearray(20)
    out[:16] = cipher.encrypt(bytes(p[:16]))
    out[16:20] = rc4_apply(key, p[16:20])
    return bytes(out)


def decrypt_packet(ct, key):
    cipher = AES.new(key, AES.MODE_ECB)
    out = bytearray(20)
    out[:16] = cipher.decrypt(bytes(ct[:16]))
    out[16:20] = rc4_apply(key, ct[16:20])
    return bytes(out)


def pkt_auth(sub):
    p = bytearray(20)
    p[0] = 0xE7
    p[1] = sub
    return bytes(p)


def session_key_from_e701(plain):
    if plain[0] != 0xE7 or plain[1] != 0x01:
        raise ValueError("expected e701, got %02x%02x" % (plain[0], plain[1]))
    return bytes(plain[2:18])


def pkt_power(on):
    p = bytearray(20)
    p[0:3] = bytes([0x33, 0x01, 0x01 if on else 0x00])
    return bytes(p)


def pkt_brightness(level):
    p = bytearray(20)
    p[0:3] = bytes([0x33, 0x04, max(0, min(100, level))])
    return bytes(p)


def pkt_color(r, g, b):
    p = bytearray(20)
    p[0:6] = bytes([0x33, 0x05, 0x0D, r, g, b])
    return bytes(p)


def pkt_aa(cmd):
    p = bytearray(20)
    p[0] = 0xAA
    p[1] = cmd
    return bytes(p)


async def send_plain(client, key, plain):
    pkt = encrypt_packet(plain, key)
    logger.debug("SEND %s", pkt.hex())
    await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, pkt, response=False)


async def wait_plain(q, key, pred, timeout=3.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError("notify timeout")
        ct = await asyncio.wait_for(q.get(), remaining)
        if len(ct) < 20:
            continue
        plain = decrypt_packet(ct[:20], key)
        if pred(plain):
            return plain


async def authenticate(client, q):
    logger.info("Authenticating")
    await client.write_gatt_char(
        SEND_CHARACTERISTIC_UUID,
        encrypt_packet(pkt_auth(0x01), PSK),
        response=False,
    )
    e701 = await wait_plain(q, PSK, lambda p: p[0] == 0xE7 and p[1] == 0x01)
    key = session_key_from_e701(e701)
    await client.write_gatt_char(
        SEND_CHARACTERISTIC_UUID,
        encrypt_packet(pkt_auth(0x02), PSK),
        response=False,
    )
    try:
        await wait_plain(q, PSK, lambda p: p[0] == 0xE7 and p[1] == 0x02, timeout=0.8)
    except TimeoutError:
        pass
    await asyncio.sleep(0.08)
    return key



def parse_aa01(pkt):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x01:
        return None
    return pkt[2] != 0


def parse_aa04(pkt):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x04:
        return None
    return pkt[2]


def parse_aa05(pkt):
    if len(pkt) < 6 or pkt[0] != 0xAA or pkt[1] != 0x05:
        return None
    if pkt[2] not in (0x0D, 0x02):
        return None
    return pkt[3], pkt[4], pkt[5]


if __name__ == "__main__":
    # Captured 2026-08-09, phone ↔ GVH600B4F5A
    n1 = bytes.fromhex("9e6122db157166686c5d658a2de1cdfbc9202c8e")
    plain = decrypt_packet(n1, PSK)
    assert plain[:2] == bytes([0xE7, 0x01])
    sess = session_key_from_e701(plain)
    power_off = decrypt_packet(
        bytes.fromhex("3ced005c862462cb58c0fa5753826089c5128c78"), sess
    )
    assert power_off[:3] == bytes([0x33, 0x01, 0x00])
    red = decrypt_packet(
        bytes.fromhex("9eea057b3a50524ada34503afca43690c5128c8e"), sess
    )
    assert red[:6] == bytes([0x33, 0x05, 0x0D, 0xFF, 0x00, 0x00])
    print("captured e701 / power-off / red decrypt ok")
