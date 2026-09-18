#!/usr/bin/env python3
"""H600B solid bulb. Auth, then encrypt every 20-byte frame.

  python cli.py frames
  python cli.py scan
  python cli.py paint --name GVH600B --rgb ff0000 --dim 40
  python cli.py status --name GVH600B
"""

import argparse
import asyncio
import sys
import time

from crypto import PSK, decrypt_packet, encrypt_packet, pkt_auth, session_key_from_e701
from packets import (
    CTRL,
    NOTIFY,
    aa_query,
    brightness,
    color_0d,
    hex20,
    parse_brightness,
    parse_color,
    parse_power,
    power,
)

GAP = 0.08


def parse_rgb(s):
    s = s.strip().lstrip("#")
    if "," in s:
        r, g, b = [int(p) for p in s.split(",")]
        return r, g, b
    if len(s) != 6:
        raise argparse.ArgumentTypeError("rgb is RRGGBB or R,G,B")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


async def find(prefix):
    from bleak import BleakScanner

    found = await BleakScanner.discover(timeout=5.0, return_adv=True)
    hits = []
    for _addr, (dev, adv) in found.items():
        name = adv.local_name or ""
        if name.startswith(prefix) or prefix.lower() in name.lower():
            hits.append((dev, name))
    return hits


async def inbox(client):
    q = asyncio.Queue()

    def on_notify(_sender, data):
        q.put_nowait(bytes(data))

    await client.start_notify(NOTIFY, on_notify)
    return q


async def wait_plain(q, key, pred, timeout=3.0):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("notify timeout")
        ct = await asyncio.wait_for(q.get(), remaining)
        if len(ct) < 20:
            continue
        plain = decrypt_packet(ct[:20], key)
        if pred(plain):
            return plain


async def auth(client, q):
    await client.write_gatt_char(CTRL, encrypt_packet(pkt_auth(0x01), PSK), response=False)
    e701 = await wait_plain(q, PSK, lambda p: p[0] == 0xE7 and p[1] == 0x01)
    key = session_key_from_e701(e701)
    await client.write_gatt_char(CTRL, encrypt_packet(pkt_auth(0x02), PSK), response=False)
    try:
        await wait_plain(q, PSK, lambda p: p[0] == 0xE7 and p[1] == 0x02, timeout=0.8)
    except TimeoutError:
        pass
    await asyncio.sleep(GAP)
    return key


async def send(client, key, plain):
    await client.write_gatt_char(CTRL, encrypt_packet(plain, key), response=False)
    await asyncio.sleep(GAP)


async def query_aa(client, q, key, cmd):
    await send(client, key, aa_query(cmd))
    return await wait_plain(
        q, key, lambda p: len(p) >= 2 and p[0] == 0xAA and p[1] == cmd
    )


def cmd_frames(_args):
    print("power on (plain) ", hex20(power(True)))
    print("rgb red (plain)  ", hex20(color_0d(255, 0, 0)))
    print("aa 01 (plain)    ", hex20(aa_query(0x01)))
    print("e701 under PSK   ", hex20(encrypt_packet(pkt_auth(0x01), PSK)))


async def cmd_scan(args):
    hits = await find(args.name)
    if not hits:
        print("no devices. Force-quit Govee and retry.", file=sys.stderr)
        return 1
    for dev, name in hits:
        print(f"{dev.address}  {name}")
    return 0


async def connect(prefix):
    from bleak import BleakClient

    hits = await find(prefix)
    if not hits:
        raise SystemExit("device not found (force-quit Govee)")
    dev, name = hits[0]
    print(f"using {dev.address} {name}", file=sys.stderr)
    return BleakClient(dev)


async def cmd_paint(args):
    r, g, b = args.rgb
    client = await connect(args.name)
    async with client:
        q = await inbox(client)
        await asyncio.sleep(0.12)
        key = await auth(client, q)
        await send(client, key, color_0d(r, g, b))
        await send(client, key, power(True))
        await send(client, key, brightness(args.dim))
    return 0


async def cmd_status(args):
    client = await connect(args.name)
    async with client:
        q = await inbox(client)
        await asyncio.sleep(0.12)
        key = await auth(client, q)
        p01 = await query_aa(client, q, key, 0x01)
        p04 = await query_aa(client, q, key, 0x04)
        p05 = await query_aa(client, q, key, 0x05)
        rgb = parse_color(p05)
        rgb_s = None if rgb is None else f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        print(f"power={parse_power(p01)} dim={parse_brightness(p04)} rgb={rgb_s}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="GVH600B", help="ADV name prefix")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("frames")
    sub.add_parser("scan")
    paint = sub.add_parser("paint")
    paint.add_argument("--rgb", type=parse_rgb, default=parse_rgb("ff0000"))
    paint.add_argument("--dim", type=int, default=100)
    sub.add_parser("status")
    args = p.parse_args()
    if args.cmd == "frames":
        cmd_frames(args)
        return 0
    return asyncio.run(
        {"scan": cmd_scan, "paint": cmd_paint, "status": cmd_status}[args.cmd](args)
    )


if __name__ == "__main__":
    raise SystemExit(main())
