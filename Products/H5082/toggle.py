#!/usr/bin/env python3

import argparse
import asyncio
import logging
import time
from bleak import BleakClient
from utils import find_device, compute_xor, SEND_CHARACTERISTIC_UUID, RECV_CHARACTERISTIC_UUID

## Configuration
DEVICE_NAME = "ihoment_H5082_1234"  # the name of the device we want to pair with
AUTH_KEY = "0db6be0625333430"  # Obtain this using pair.py


MSG_LEFT_ON = "3301220000000000000000000000000000000010"
MSG_LEFT_OFF = "3301200000000000000000000000000000000012"
MSG_RIGHT_ON = "3301110000000000000000000000000000000023"
MSG_RIGHT_OFF = "3301100000000000000000000000000000000022"


logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(levelname)s: %(message)s",
    )
logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG

async def main(toggle_side):
  logger.info(f"Searching for device {DEVICE_NAME}")
  device, adv_data = await find_device(DEVICE_NAME)
  if device is None:
    logger.error(f"Could not find a device!")
    return

  # Read the state of the switch at this moment
  state = get_adv_on_state(adv_data)
  if state is None:
    logger.error(f"Could not detect the current state")
    return
  l, r = state
  logger.info(f"Device state is: left={l} right={r}")

  logger.info(f"Connecting...")

  # Connect 
  async with BleakClient(device.address) as client:
    logger.info(f"Connected to {client.address}")
    
    # events to control execution flow
    on_auth_ready = asyncio.Event()
    on_set_state_ready = asyncio.Event()

    async def recv_handler(c, data):
      logger.debug(f"RECV {data.hex()}")
      if data[0] == 0x33 and data[1] == 0xB2:
        on_auth_ready.set()
      elif data[0] == 0x33 and data[1] == 0x01:
        on_set_state_ready.set()

    await client.start_notify(RECV_CHARACTERISTIC_UUID, recv_handler)
    
    await authenticate(client, AUTH_KEY)
    await on_auth_ready.wait()

    if toggle_side == "left":
      await set_left_state(client, not l)
    elif toggle_side == "right":
      await set_right_state(client, not r)
    else:
      assert False

    await on_set_state_ready.wait()

    await client.stop_notify(RECV_CHARACTERISTIC_UUID)
    logger.info("Finished")



# Parses the advertisement data for useful information (i.e. the on/off state)
def get_adv_on_state(adv_data):
    for mfr_id, mfr_data in adv_data.manufacturer_data.items():
      # The last byte in the manufacturer data is the state of the switch
      rstate = (mfr_data[-1] & 0x1) == 0x1
      lstate = (mfr_data[-1] & 0x2) == 0x2
      return lstate, rstate
    return None


async def authenticate(client, auth_key):
  logger.info("Authenticating")
  # Create the message
  ba = bytearray([0x33, 0xB2]) + bytearray.fromhex(auth_key).ljust(17, b'\0')
  ba.append(compute_xor(ba))  
  logger.debug(f"SEND {ba.hex()}")
  await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, ba)


async def set_left_state(client, new_state):
  logger.info(f"Updating left state to {new_state}")
  # Send the set on or off command
  ba = bytearray.fromhex(MSG_LEFT_ON if new_state else MSG_LEFT_OFF)
  logger.debug(f"SEND {ba.hex()}")
  await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, ba)

async def set_right_state(client, new_state):
  logger.info(f"Updating right state to {new_state}")
  # Send the set on or off command
  ba = bytearray.fromhex(MSG_RIGHT_ON if new_state else MSG_RIGHT_OFF)
  logger.debug(f"SEND {ba.hex()}")
  await client.write_gatt_char(SEND_CHARACTERISTIC_UUID, ba)

  
if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("side", choices=["left", "right"])
  args = parser.parse_args()
  asyncio.run(main(args.side))