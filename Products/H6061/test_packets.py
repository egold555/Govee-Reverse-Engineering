#!/usr/bin/env python3
import unittest

from packets import (
    aa_a5,
    aa_query,
    brightness,
    hex20,
    panel_color,
    parse_a5,
    parse_brightness,
    parse_power,
    power,
    seg_brightness,
    seg_color,
)


class TestH6061(unittest.TestCase):
    def test_documented_samples(self):
        self.assertEqual(
            hex20(power(True)),
            "33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33",
        )
        self.assertEqual(
            hex20(power(False)),
            "33 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 32",
        )
        self.assertEqual(
            hex20(brightness(100)),
            "33 04 64 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 53",
        )
        self.assertEqual(
            hex20(brightness(10)),
            "33 04 0a 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 3d",
        )
        self.assertEqual(
            hex20(panel_color(1, 0xFF, 0, 0)),
            "33 05 15 01 ff 00 00 00 00 01 00 00 00 00 00 00 00 00 00 dc",
        )
        self.assertEqual(
            hex20(panel_color(10, 0, 0xFF, 0xFF)),
            "33 05 15 01 00 ff ff 00 00 00 02 00 00 00 00 00 00 00 00 20",
        )

    def test_mask_bytes(self):
        color = seg_color(0x1234, 1, 2, 3)
        self.assertEqual(color[9:11], bytes([0x12, 0x34]))
        dim = seg_brightness(0x1234, 42)
        self.assertEqual(dim[5:7], bytes([0x12, 0x34]))
        self.assertEqual(dim[4], 42)

    def test_checksum_folds_to_zero(self):
        for pkt in (
            power(True),
            brightness(42),
            panel_color(8, 1, 2, 3),
            aa_query(0x01),
            aa_a5(1),
        ):
            x = 0
            for b in pkt:
                x ^= b
            self.assertEqual(x, 0)
            self.assertEqual(len(pkt), 20)

    def test_status_parse(self):
        off = bytes.fromhex("aa010000000000000000000000000000000000ab")
        on = bytes.fromhex("aa010100000000000000000000000000000000aa")
        dim = bytes.fromhex("aa040500000000000000000000000000000000ab")
        self.assertEqual(parse_power(off), False)
        self.assertEqual(parse_power(on), True)
        self.assertEqual(parse_brightness(dim), 5)

        page1 = bytes.fromhex(
            "aaa5016400ffae6400ffb76421ff976440ffaf4e"
        )
        page, slots = parse_a5(page1)
        self.assertEqual(page, 1)
        self.assertEqual(slots[0], (100, 0x00, 0xFF, 0xAE))
        self.assertEqual(slots[3], (100, 0x40, 0xFF, 0xAF))


if __name__ == "__main__":
    unittest.main()
