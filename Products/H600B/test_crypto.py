#!/usr/bin/env python3
import unittest

from crypto import PSK, decrypt_packet, encrypt_packet, session_key_from_e701
from packets import color_0d, parse_color, parse_power, power


class TestH600B(unittest.TestCase):
    def test_captured_auth_and_commands(self):
        # 2026-08-09 PCAP, phone ↔ GVH600B4F5A
        n1 = bytes.fromhex("9e6122db157166686c5d658a2de1cdfb c9202c8e".replace(" ", ""))
        plain = decrypt_packet(n1, PSK)
        self.assertEqual(plain[:2], bytes([0xE7, 0x01]))
        sess = session_key_from_e701(plain)
        self.assertEqual(
            sess,
            bytes(
                [
                    0x27,
                    0x54,
                    0x81,
                    0xAE,
                    0xDC,
                    0x09,
                    0x36,
                    0x64,
                    0x91,
                    0xBE,
                    0xEC,
                    0x19,
                    0x46,
                    0x73,
                    0xA1,
                    0xCE,
                ]
            ),
        )

        power_off = decrypt_packet(
            bytes.fromhex("3ced005c862462cb58c0fa5753826089 c5128c78".replace(" ", "")),
            sess,
        )
        self.assertEqual(power_off[:3], bytes([0x33, 0x01, 0x00]))

        red = decrypt_packet(
            bytes.fromhex("9eea057b3a50524ada34503afca43690 c5128c8e".replace(" ", "")),
            sess,
        )
        self.assertEqual(red[:6], bytes([0x33, 0x05, 0x0D, 0xFF, 0x00, 0x00]))

    def test_encrypt_round_trip(self):
        ct = encrypt_packet(power(True), PSK)
        back = decrypt_packet(ct, PSK)
        self.assertEqual(back[:3], bytes([0x33, 0x01, 0x01]))
        x = 0
        for b in back[:19]:
            x ^= b
        self.assertEqual(back[19], x)

    def test_status_parse(self):
        off = bytes.fromhex("aa010000000000000000000000000000000000ab")
        red = bytes.fromhex("aa050dff0000000000000000000000000000005d")
        seg = bytes.fromhex("aa051500000000000000000000000000000000ba")
        self.assertEqual(parse_power(off), False)
        self.assertEqual(parse_color(red), (255, 0, 0))
        self.assertIsNone(parse_color(seg))
        self.assertEqual(color_0d(255, 0, 0)[:6], bytes([0x33, 0x05, 0x0D, 255, 0, 0]))


if __name__ == "__main__":
    unittest.main()
