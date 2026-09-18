#!/usr/bin/env python3
"""Paint or read an H6061 over BLE. Force-quit the Govee app first.

  python cli.py frames
  python cli.py scan
  python cli.py paint --name Govee_H6061 --panel 1 --rgb ff0000 --dim 10
  python cli.py status --name Govee_H6061
"""

import argparse
import asyncio
import sys
import time

from packets import (
    CTRL,
    NOTIFY,
    PANEL_MASK,
    aa_a5,
    aa_query,
    brightness,
    hex20,
    panel_color,
    parse_a5,
    parse_brightness,
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


async def write20(client, pkt):
    await client.write_gatt_char(CTRL, pkt, response=False)
    await asyncio.sleep(GAP)


async def inbox(client):
    q = asyncio.Queue()

    def on_notify(_sender, data):
        q.put_nowait(bytes(data))

    await client.start_notify(NOTIFY, on_notify)
    return q


async def wait_aa(q, cmd, timeout=3.0):
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"no aa {cmd:02x} notify")
        pkt = await asyncio.wait_for(q.get(), remaining)
        if len(pkt) >= 2 and pkt[0] == 0xAA and pkt[1] == cmd:
            return pkt


def cmd_frames(_args):
    print("power on ", hex20(power(True)))
    print("power off", hex20(power(False)))
    print("dim 100  ", hex20(brightness(100)))
    for n in range(1, 11):
        print(f"panel {n:2d} red  {hex20(panel_color(n, 255, 0, 0))}")
    print("aa 01    ", hex20(aa_query(0x01)))
    print("aa 04    ", hex20(aa_query(0x04)))
    print("aa a5 1  ", hex20(aa_a5(1)))


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
        await write20(client, power(True))
        if args.all:
            for n in PANEL_MASK:
                await write20(client, panel_color(n, r, g, b))
        else:
            await write20(client, panel_color(args.panel, r, g, b))
        await write20(client, brightness(args.dim))
    return 0


async def cmd_status(args):
    client = await connect(args.name)
    async with client:
        q = await inbox(client)
        await asyncio.sleep(0.12)
        await write20(client, aa_query(0x01))
        p01 = await wait_aa(q, 0x01)
        await write20(client, aa_query(0x04))
        p04 = await wait_aa(q, 0x04)
        print(f"power={parse_power(p01)} dim={parse_brightness(p04)}")
        colors = []
        for page in (1, 2, 3):
            await write20(client, aa_a5(page))
            pkt = await wait_aa(q, 0xA5)
            _pg, slots = parse_a5(pkt)
            colors.extend(slots)
        for i, (pct, r, g, b) in enumerate(colors[:10], start=1):
            print(f"panel {i:2d}  {pct:3d}%  #{r:02x}{g:02x}{b:02x}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="Govee_H6061", help="ADV name prefix")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("frames", help="print sample hex, no BLE")
    sub.add_parser("scan")
    paint = sub.add_parser("paint")
    paint.add_argument("--panel", type=int, default=1, choices=range(1, 11))
    paint.add_argument("--all", action="store_true", help="paint every panel")
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
