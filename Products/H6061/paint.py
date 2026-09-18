#!python3
import asyncio
import logging
from bleak import BleakClient
from utils import (
    PANEL_MASK,
    find_device,
    pkt_brightness,
    pkt_panel_color,
    pkt_power,
    send,
)

## Configuration
DEVICE_NAME = "Govee_H6061"  # substring of the advertised name
PANEL = 1  # 1–10. Set PAINT_ALL True to hit every panel
PAINT_ALL = False
COLOR = (255, 0, 0)
BRIGHTNESS = 100  # 0–100 wall dim, after color

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

        panels = PANEL_MASK if PAINT_ALL else [PANEL]
        r, g, b = COLOR
        for n in panels:
            logger.info("panel %s -> %s", n, COLOR)
            await send(client, pkt_panel_color(n, r, g, b))
            await asyncio.sleep(0.08)

        await send(client, pkt_brightness(BRIGHTNESS))
        logger.info("Finished")


asyncio.run(main())
