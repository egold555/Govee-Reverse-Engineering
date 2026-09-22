import logging
from bleak import BleakScanner

SEND_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
RECV_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

# Mask bit at **byte 12**, not Hexa bytes 9–10.
CUBE_BIT = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20}

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


def make_packet(ba):
    pkt = bytearray(ba).ljust(19, b"\0")[:19]
    pkt.append(compute_xor(pkt))
    return pkt


def pkt_power(on):
    return make_packet([0x33, 0x01, 0x01 if on else 0x00])


def pkt_brightness(level):
    return make_packet([0x33, 0x04, max(0, min(100, level))])


def pkt_cube_color(mask_bit, r, g, b):
    p = bytearray(19)
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x01])
    p[4:7] = bytes([r, g, b])
    p[12] = mask_bit & 0xFF
    return make_packet(p)


def pkt_cube_brightness(mask_bit, level):
    p = bytearray(19)
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x02])
    p[4] = max(0, min(100, level))
    p[5] = mask_bit & 0xFF
    return make_packet(p)


def pkt_cube_n_color(n, r, g, b):
    return pkt_cube_color(CUBE_BIT[n], r, g, b)


def pkt_aa(cmd, extra=b""):
    p = bytearray(19)
    p[0] = 0xAA
    p[1] = cmd
    p[2 : 2 + len(extra)] = extra
    return make_packet(p)


async def send(client, pkt):
    logger.debug("SEND %s", pkt.hex())
    await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, pkt, response=False)


def parse_aa01(pkt):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x01:
        return None
    return pkt[2] != 0


def parse_aa04(pkt):
    if len(pkt) < 3 or pkt[0] != 0xAA or pkt[1] != 0x04:
        return None
    return pkt[2]


def parse_aaa5(pkt):
    if len(pkt) < 19 or pkt[0] != 0xAA or pkt[1] != 0xA5:
        return None
    page = pkt[2]
    slots = []
    for i in range(4):
        o = 3 + i * 4
        slots.append((pkt[o], pkt[o + 1], pkt[o + 2], pkt[o + 3]))
    return page, slots


if __name__ == "__main__":
    assert pkt_cube_n_color(1, 255, 0, 0).hex() == "33051501ff0000000000000001000000000000dc"
    assert pkt_cube_n_color(6, 0, 255, 255).hex() == "3305150100ffff00000000002000000000000002"
    print("H6088 sample frames ok")

