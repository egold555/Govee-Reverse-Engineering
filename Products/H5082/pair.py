#!/usr/bin/env python3
import asyncio
import logging
import time
from bleak import BleakClient
from utils import find_device, SEND_CHARACTERISTIC_UUID, RECV_CHARACTERISTIC_UUID

## Configuration
DEVICE_NAME = "ihoment_H5082_1234"  # the name of the device we want to pair with

MSG_GET_AUTH_KEY = "aab100000000000000000000000000000000001b"

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)-15s %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG


async def main():
  logger.info(f"Searching for device {DEVICE_NAME}")
  device, _ = await find_device(DEVICE_NAME)
  if device is None:
    logger.error(f"Could not find a device!")
    return

  logger.info(f"Connecting...")

  async with BleakClient(device.address) as client:
    logger.info(f"Connected to {client.address}")
    logger.info("Starting pairing process...")

    stop_event = asyncio.Event()

    async def recv_handler(charact, msg):
      if len(msg) != 20:
        return 

      # Check for the response type and subtype
      if msg[0] == 0xAA and msg[1] == 0xB1:
        auth_key = extract_auth_key(msg)
        if auth_key is not None:
          logger.info(f"Retrieved authentication key: {auth_key.hex()}")
          stop_event.set()
        else:          
          logger.debug(f"Invalid auth key message: ({msg.hex()})")
          logger.info(f"Press the physical button on the device!")
          time.sleep(0.2)
          await send_get_auth_key(client)

    await client.start_notify(RECV_CHARACTERISTIC_UUID, recv_handler)
    await send_get_auth_key(client)
    await stop_event.wait()
    await client.stop_notify(RECV_CHARACTERISTIC_UUID)


def extract_auth_key(msg):
  # If first byte in payload is 0x00, it means the key is not good
  if msg[2] != 0x01:
    return None
  key = msg[3:-1]
  return key

async def send_get_auth_key(client):
  ba = bytearray.fromhex(MSG_GET_AUTH_KEY)
  await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, ba)

asyncio.run(main())