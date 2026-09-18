import logging
from bleak import BleakScanner

SEND_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
RECV_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

# 1 = power injector, then along the snake to 10. Mask is u16 BE at bytes 9–10.
PANEL_MASK = {
    1: 0x0100,
    2: 0x0200,
    3: 0x0400,
    4: 0x0800,
    5: 0x1000,
    6: 0x2000,
    7: 0x4000,
    8: 0x8000,
    9: 0x0001,
    10: 0x0002,
}

logger = logging.getLogger(__name__)


async def find_device(name):
    """First advertisement whose local name contains `name`."""
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
    """19 useful bytes (or fewer); pad and append XOR checksum."""
    pkt = bytearray(ba).ljust(19, b"\0")[:19]
    pkt.append(compute_xor(pkt))
    return pkt


def pkt_power(on):
    return make_packet([0x33, 0x01, 0x01 if on else 0x00])


def pkt_brightness(level):
    return make_packet([0x33, 0x04, max(0, min(100, level))])


def pkt_seg_color(mask, r, g, b):
    p = bytearray(19)
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x01])
    p[4:7] = bytes([r, g, b])
    p[9] = (mask >> 8) & 0xFF
    p[10] = mask & 0xFF
    return make_packet(p)


def pkt_seg_brightness(mask, level):
    p = bytearray(19)
    p[0:4] = bytes([0x33, 0x05, 0x15, 0x02])
    p[4] = max(0, min(100, level))
    p[5] = (mask >> 8) & 0xFF
    p[6] = mask & 0xFF
    return make_packet(p)


def pkt_panel_color(panel, r, g, b):
    return pkt_seg_color(PANEL_MASK[panel], r, g, b)


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
    assert pkt_power(True).hex() == "3301010000000000000000000000000000000033"
    assert pkt_panel_color(1, 255, 0, 0).hex() == "33051501ff0000000001000000000000000000dc"
    assert pkt_panel_color(10, 0, 255, 255).hex() == "3305150100ffff00000002000000000000000020"
    print("H6061 sample frames ok")

