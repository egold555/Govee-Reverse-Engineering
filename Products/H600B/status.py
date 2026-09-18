#!python3
import asyncio
import logging
from bleak import BleakClient
from utils import (
    RECV_CHARACTERISTIC_UUID,
    authenticate,
    find_device,
    parse_aa01,
    parse_aa04,
    parse_aa05,
    pkt_aa,
    send_plain,
    wait_plain,
)

## Configuration
DEVICE_NAME = "GVH600B"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG


async def query_aa(client, q, key, cmd):
    await send_plain(client, key, pkt_aa(cmd))
    return await wait_plain(
        q, key, lambda p: len(p) >= 2 and p[0] == 0xAA and p[1] == cmd
    )


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
        key = await authenticate(client, q)

        p01 = await query_aa(client, q, key, 0x01)
        p04 = await query_aa(client, q, key, 0x04)
        p05 = await query_aa(client, q, key, 0x05)
        rgb = parse_aa05(p05)
        rgb_s = None if rgb is None else "#%02x%02x%02x" % rgb
        logger.info("power=%s dim=%s rgb=%s", parse_aa01(p01), parse_aa04(p04), rgb_s)
        await client.stop_notify(RECV_CHARACTERISTIC_UUID)
        logger.info("Finished")


asyncio.run(main())
