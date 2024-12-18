#!/usr/bin/env python3
#
# Uses ha_mqtt_discoverable to publish several devices to home assistant via
# MQTT. You need to pair with the H5080 using pair.py, and then create a
# `devices.toml` that has a list like so:
#
#   [[devices]]
#   name = "G1"
#   uid = "ihoment_H5080_5241"
#   auth = "xxxxx"
#
# See "DeviceConfig" for parameter descriptions.
#

import asyncio
import contextlib
import dataclasses
import logging
import typing as T

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Switch, SwitchInfo
from paho.mqtt.client import Client, MQTTMessage

import tomli
import validobj

from toggle import authenticate, set_state, RECV_CHARACTERISTIC_UUID

logger = logging.getLogger(__name__)

#
# Configuration
#


@dataclasses.dataclass
class DeviceConfig:
    # Entity shown to home assistant
    name: str
    # Device's unique id (obtain via scan)
    uid: str
    # Authentation token (obtain via pair)
    auth: str


@dataclasses.dataclass
class TomlConfig:
    """
    Contains a list of [[devices]] entries
    """

    devices: T.List[DeviceConfig]


@dataclasses.dataclass
class DeviceData:
    """
    Primary data structure
    """

    cfg: DeviceConfig
    device_lock: asyncio.Lock
    ble_device: T.Optional[BLEDevice] = None
    switch: T.Optional[Switch] = None
    state: T.Optional[bool] = None


def ha_switch_callback(
    client: Client,
    set_state: T.Callable[[bool], None],
    message: MQTTMessage,
):
    payload = message.payload.decode()
    onoff = None
    if payload == "ON":
        onoff = True

    elif payload == "OFF":
        onoff = False

    if onoff is not None:
        set_state(onoff)


async def set_device_state(data: DeviceData, onoff: bool, lock: asyncio.Lock):

    async with contextlib.AsyncExitStack() as stack:

        # Only allow a single connection at once
        for i in range(3):
            if i != 0:
                await asyncio.sleep(3)

            async with (lock, data.device_lock):
                logger.info(
                    f"set_device_state: %s on=%s attempt=%d",
                    data.cfg.name,
                    onoff,
                    i,
                )

                if data.ble_device is None:
                    logger.warning("attempt %d failed: device not found", i)
                    continue

                try:

                    client = BleakClient(data.ble_device)
                    await stack.enter_async_context(client)
                    break
                except Exception as e:
                    # seems to be lots of ways this can fail
                    logger.warning("attempt %d failed: %s", i, e)
                    pass
        else:
            logger.error("set_device_state for %s failed", data.cfg.name)
            return

        logger.info(f"Connected to {data.cfg.name} ({client.address})")

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

        await authenticate(client, data.cfg.auth)
        await on_auth_ready.wait()

        await set_state(client, onoff)
        await on_set_state_ready.wait()

        await client.stop_notify(RECV_CHARACTERISTIC_UUID)
        logger.info("Command completed")

        # If this isn't here then there's a lag..
        assert data.switch is not None
        if onoff:
            data.switch.on()
        else:
            data.switch.off()


def make_setstate_fn(
    loop: asyncio.AbstractEventLoop, data: DeviceData, lock: asyncio.Lock
):

    def _set_device_state_done(f):
        try:
            f.result()
        except:
            logger.exception("set_device_state for %s failed", data.cfg.name)

    def _set_device_threadsafe(onoff: bool):
        f = asyncio.run_coroutine_threadsafe(set_device_state(data, onoff, lock), loop)

        f.add_done_callback(_set_device_state_done)

    return _set_device_threadsafe


async def main():
    mqtt_settings = Settings.MQTT(host="localhost")

    with open("devices.toml", "rb") as fp:
        raw_config = tomli.load(fp)
        config = validobj.validation.parse_input(raw_config, TomlConfig)

    devices: T.Dict[str, DeviceData] = {}

    #
    # Set up entities
    #

    loop = asyncio.get_running_loop()
    lock = asyncio.Lock()

    for devinfo in config.devices:
        sinfo = SwitchInfo(name=devinfo.name)
        settings = Settings(mqtt=mqtt_settings, entity=sinfo)
        data = DeviceData(devinfo, asyncio.Lock())
        devices[devinfo.uid] = data

        data.switch = Switch(
            settings, ha_switch_callback, make_setstate_fn(loop, data, lock)
        )

    #
    # poll loop
    #

    stop_event = asyncio.Event()

    async def scanner_callback(device: BLEDevice, adv: AdvertisementData):
        ddata = devices.get(adv.local_name or "")
        if ddata is None:
            return

        async with ddata.device_lock:
            ddata.ble_device = device

        for _, mfr_data in adv.manufacturer_data.items():
            is_on = mfr_data[-1] == 0x01
            state_changed = ddata.state != is_on
            ddata.state = is_on

            if state_changed:
                logger.info(
                    "%s (%s) changed: is_on=%s", ddata.cfg.name, adv.local_name, is_on
                )
                if ddata.switch:
                    if is_on:
                        ddata.switch.on()
                    else:
                        ddata.switch.off()

            break

    async with BleakScanner(scanner_callback) as scanner:
        await stop_event.wait()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)-15s %(levelname)s: %(message)s"
    )
    asyncio.run(main())
