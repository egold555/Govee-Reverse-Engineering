import logging
from bleak import BleakScanner, BleakClient

SEND_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
RECV_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

logger = logging.getLogger(__name__)
# logger.level = logging.DEBUG

async def find_device(name):
  devices = await BleakScanner.discover(timeout=5.0, return_adv=True)
  for _, (device, adv_data) in devices.items():
    if adv_data.local_name == name:
      return (device, adv_data)
  return (None, None)

# Computes the xor of all bytes in a bytearray
# Useful to generate the checksum at the end of a govee message 
def compute_xor(ba):
  res = 0
  for b in ba:
    res = res ^ b
  return res