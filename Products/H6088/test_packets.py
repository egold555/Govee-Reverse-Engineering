#!/usr/bin/env python3
import unittest

from packets import (
    aa_a5,
    brightness,
    cube_color,
    cube_n_color,
    hex20,
    parse_a5,
    power,
)


class TestH6088(unittest.TestCase):
    def test_documented_samples(self):
        self.assertEqual(
            hex20(cube_n_color(1, 0xFF, 0, 0)),
            "33 05 15 01 ff 00 00 00 00 00 00 00 01 00 00 00 00 00 00 dc",
        )
        self.assertEqual(
            hex20(cube_n_color(6, 0, 0xFF, 0xFF)),
            "33 05 15 01 00 ff ff 00 00 00 00 00 20 00 00 00 00 00 00 02",
        )

    def test_mask_is_byte_12(self):
        pkt = cube_color(0x08, 1, 2, 3)
        self.assertEqual(pkt[12], 0x08)
        self.assertEqual(pkt[4:7], bytes([1, 2, 3]))
        self.assertEqual(pkt[9:11], bytes([0, 0]))

    def test_checksum(self):
        for pkt in (power(True), brightness(100), cube_n_color(3, 0, 255, 0), aa_a5(1)):
            x = 0
            for b in pkt:
                x ^= b
            self.assertEqual(x, 0)

    def test_a5_page(self):
        pkt = bytes.fromhex("aaa5016400ffae6421ff9764a1ffe064a1ffe016")
        page, slots = parse_a5(pkt)
        self.assertEqual(page, 1)
        self.assertEqual(slots[0], (100, 0x00, 0xFF, 0xAE))


if __name__ == "__main__":
    unittest.main()
