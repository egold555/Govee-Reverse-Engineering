#!python3
import asyncio
import logging
from bleak import BleakScanner

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(levelname)s: %(message)s",
    )
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG

async def main():
    stop_event = asyncio.Event()
    def callback(device, adv):
        if adv.local_name is None:
            return 

        logger.debug("------")
        logger.debug(device)
        logger.debug(adv.service_uuids)
        logger.debug(adv.manufacturer_data)

        if "H5080" in adv.local_name:
            for mfr_id, mfr_data in adv.manufacturer_data.items():
                is_on = mfr_data[-1] == 0x01
                state_name = "On" if is_on else "Off"
                logger.info(f"{adv.local_name}: state={state_name} (address={device.address}, mfr_data={mfr_data.hex()}) ")

    async with BleakScanner(callback) as scanner:
        await stop_event.wait()

asyncio.run(main())