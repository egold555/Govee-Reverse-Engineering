#!python3
import asyncio
import logging
from bleak import BleakClient
from utils import (
    RECV_CHARACTERISTIC_UUID,
    authenticate,
    find_device,
    pkt_brightness,
    pkt_color,
    pkt_power,
    send_plain,
)

## Configuration
DEVICE_NAME = "GVH600B"
COLOR = (255, 0, 0)
BRIGHTNESS = 100

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG


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

        r, g, b = COLOR
        # Phone order: color, power on, brightness
        await send_plain(client, key, pkt_color(r, g, b))
        await asyncio.sleep(0.08)
        await send_plain(client, key, pkt_power(True))
        await asyncio.sleep(0.08)
        await send_plain(client, key, pkt_brightness(BRIGHTNESS))
        await client.stop_notify(RECV_CHARACTERISTIC_UUID)
        logger.info("Finished")


asyncio.run(main())
