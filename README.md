# Govee-H6113-Reverse-Engineering
My attempt at reverse engineering the Govee H6113 RGB lighting strips BLE commands.

------
# A Message to Govee

>In the U.S., Section 103(f) of the Digital Millennium Copyright Act (DMCA) [(17 USC § 1201 (f) - Reverse Engineering)](https://www.law.cornell.edu/uscode/text/17/1201) specifically states that it is legal to reverse engineer and circumvent the protection to achieve interoperability between computer programs (such as information transfer between applications). Interoperability is defined in paragraph 4 of Section 103(f).
>
>It is also often lawful to reverse-engineer an artifact or process as long as it is obtained legitimately. If the software is patented, it doesn't necessarily need to be reverse-engineered, as patents require a public disclosure of invention. It should be mentioned that, just because a piece of software is patented, that does not mean the entire thing is patented; there may be parts that remain undisclosed.


Govee I love your product, and I mean no harm in releasing this information. I only did this as a side project so I can control the lighting strips from my own app that runs in my car. I decided to publish my findings and protocol reverse engineering so that anyone else who is looking to do the same might have a place to start. Long story short, __please don't sue me, or DMCA this repo__. If you wish for me to take it down, __please email me or leave a issue on this repo stating that you would like it to be removed, and I will happily do so__.

With all that out of the way, on to the documentation!

# My Findings

I have only tested this on the Govee H6113 so I am unsure if these packets or UUID's work for anything else.

### Checklist of packets
- [x] Keep alive
- [x] Change Color
- [x] Set global brightness
- [ ] Change to music mode
- [ ] Change music mode to cycle colors

### How packets work
From my understanding, all packets are 20 bytes long. The first byte is a identifier, followed by 18 bytes of data, followed by a XOR of all the bytes.

```
IDENTIFIER, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, DATA, XOR
```

| Type           | Unformatted UUID                 | Formatted UUID                       |
|----------------|----------------------------------|--------------------------------------|
| Service        | 000102030405060708090a0b0c0d1910 | 00010203-0405-0607-0809-0a0b0c0d1910 |
| Characteristic | 000102030405060708090a0b0c0d2b11 | 00010203-0405-0607-0809-0a0b0c0d2b11 |




### Keep Alive
It is always this, it never seems to change. This is sent every 2 seconds from the mobile app to the device.
```
0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xAB
```

### Set Color
RED, GREEN, BLUE range is 0 - 255 or 0x00 - 0xFF
```
0x33, 0x05, 0x02, RED, GREEN, BLUE, 0x00, 0xFF, 0xAE, 0x54, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, (0x31 ^ RED ^ GREEN ^ BLUE)
```

### Set Brightness
BRIGHTNESS range is 0 - 255 or 0x00 - 0xFF
```
0x33, 0x04, BRIGHTNESS, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, (0x33 ^ 0x04 ^ BRIGHTNESS)
```
