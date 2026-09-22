#!python3
import asyncio
import logging
from bleak import BleakScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEVICE_NAME = "H6088"


async def main():
    logger.info("Scanning for %s", DEVICE_NAME)
    devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
    found = False
    for _, (device, adv) in devices.items():
        name = adv.local_name or ""
        if DEVICE_NAME not in name:
            continue
        found = True
        logger.info("%s  %s", device.address, name)
    if not found:
        logger.error("No device. Force-quit the Govee app and retry.")


asyncio.run(main())
