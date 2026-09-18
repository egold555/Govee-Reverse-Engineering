#!python3
import asyncio
import logging
from bleak import BleakClient
from utils import (
    RECV_CHARACTERISTIC_UUID,
    find_device,
    parse_aa01,
    parse_aa04,
    parse_aaa5,
    pkt_aa,
    send,
)

## Configuration
DEVICE_NAME = "Govee_H6061"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG


async def wait_aa(q, cmd, timeout=3.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError("no aa %02x notify" % cmd)
        pkt = await asyncio.wait_for(q.get(), remaining)
        if len(pkt) >= 2 and pkt[0] == 0xAA and pkt[1] == cmd:
            return pkt


async def main():
    logger.info("Searching for device %s", DEVICE_NAME)
    device, _adv = await find_device(DEVICE_NAME)
    if device is None:
        logger.error("Could not find a device! Force-quit Govee and retry.")
        return

    logger.info("Connecting...")
    async with BleakClient(device.address) as client:
        logger.info("Connected to %s", client.address)
        q = asyncio.Queue()

        def recv_handler(_c, data):
            logger.debug("RECV %s", data.hex())
            q.put_nowait(bytes(data))

        await client.start_notify(RECV_CHARACTERISTIC_UUID, recv_handler)
        await asyncio.sleep(0.12)

        await send(client, pkt_aa(0x01))
        p01 = await wait_aa(q, 0x01)
        await asyncio.sleep(0.08)
        await send(client, pkt_aa(0x04))
        p04 = await wait_aa(q, 0x04)
        logger.info("power=%s dim=%s", parse_aa01(p01), parse_aa04(p04))

        colors = []
        for page in (1, 2, 3):
            await send(client, pkt_aa(0xA5, bytes([page])))
            pkt = await wait_aa(q, 0xA5)
            _page, slots = parse_aaa5(pkt)
            colors.extend(slots)
            await asyncio.sleep(0.08)

        for i, (pct, r, g, b) in enumerate(colors[:10], start=1):
            logger.info("panel %2d  %3d%%  #%02x%02x%02x", i, pct, r, g, b)

        await client.stop_notify(RECV_CHARACTERISTIC_UUID)
        logger.info("Finished")


asyncio.run(main())
