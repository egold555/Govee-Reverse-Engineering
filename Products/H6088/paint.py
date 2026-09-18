#!python3
import asyncio
import logging
from bleak import BleakClient
from utils import (
    CUBE_BIT,
    find_device,
    pkt_brightness,
    pkt_cube_n_color,
    pkt_power,
    send,
)

## Configuration
DEVICE_NAME = "Govee_H6088"
CUBE = 1  # 1–6. Set PAINT_ALL True to hit every cube
PAINT_ALL = False
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
        await send(client, pkt_power(True))
        await asyncio.sleep(0.08)

        cubes = CUBE_BIT if PAINT_ALL else [CUBE]
        r, g, b = COLOR
        for n in cubes:
            logger.info("cube %s -> %s", n, COLOR)
            await send(client, pkt_cube_n_color(n, r, g, b))
            await asyncio.sleep(0.08)

        await send(client, pkt_brightness(BRIGHTNESS))
        logger.info("Finished")


asyncio.run(main())
