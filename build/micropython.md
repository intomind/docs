---
title: MicroPython
description: MicroPython for the Raspberry Pi Pico 2 W with the intomind library for the IntoMind One: install it on the board, connect and pair, stream, read what the device reports, and run heads on the device.
url: https://docs.intomind.com/micropython.html
---

# MicroPython

MicroPython for the Raspberry Pi Pico 2 W, with the `intomind` library built in, lets a program on the board connect to an IntoMind One with no computer in the room. It is MicroPython 1.29.0 as released for the Pico 2 W with pairing added, because the IntoMind One accepts commands and sends data only over a paired, encrypted link, and MicroPython as released cannot pair on the Pico 2 W. Everything else MicroPython does on the board, Wi-Fi included, works as usual.

## Install

1. Download `intomind-micropython-pico-2-w.uf2` from the `firmware` folder of [github.com/intomind/micropython](https://github.com/intomind/micropython).
2. Hold the BOOTSEL button while you plug the board into your computer, then let go. Drag the file onto the drive that appears.
3. The board restarts into MicroPython, and its banner reads `v1.29.0-intomind`. In Thonny, choose MicroPython (Raspberry Pi Pico) at the bottom right, and the prompt is the board's.

A program saved on the board as `main.py` runs whenever the board has power.

## Connect and stream

```micropython
import asyncio
import intomind


def on_packet(device, packet):
    scale = device.info.microvolts_per_count(packet.gain)
    channel_1 = [counts[0] * scale for counts in packet.counts]   # one count per channel in each row
    print(packet.index, channel_1)               # the first sample's index, and channel 1 in microvolts


async def main():
    device = await intomind.connect()            # the first IntoMind One heard
    print("Connected to", device.name)
    device.on_packet = on_packet                 # before start()
    await device.start()
    await asyncio.sleep(5)
    await device.stop()
    await device.disconnect()


asyncio.run(main())
```

`intomind.connect("Ada's")` connects to the first device whose name starts with `Ada's`, and `intomind.scan()` lists every device heard, the strongest first. The first connection pairs the board with the device, and later connections reuse the pairing, which the board keeps in `ble_secrets.json`. If a connection fails because the device no longer has the pairing, the error says to call `intomind.forget_pairings()`, and the next connection pairs again.

Each packet carries the index of its first sample. The next packet's index is this one's plus `packet.n_samples`, so a larger jump means samples were lost on the way. A stream started while the IntoMind One is plugged in is refused: `start()` raises `intomind.Refused` with status 7, because the device does not stream from its electrodes on USB power.

## What the device reports

The library holds no table of hardware. What a device can do is what it reports, and the methods for the battery, the model and heads raise `OSError` when it does not report that capability.

```micropython
device.info.channels                     # 4
device.info.rates                        # the sample rates it offers
device.can("heads")                      # True when it reports that capability
status = await device.read_status()      # streaming, battery, charger, USB, and contact
battery = await device.battery()         # millivolts, percent, and the charger
```

## Run a head

The IntoMind One runs heads on its own chip, and the board reads what they say. Train one in [Python](https://docs.intomind.com/python.html#the-model), or upload one from [JavaScript](https://docs.intomind.com/javascript.html#run-your-own-head).

```micropython
active, heads = await device.heads()
for head in heads:
    print(head.slot, head.name, head.state)      # "valid" when it can run


def on_prediction(device, p):
    if not (p.gap_in_window or p.leadoff_in_window):    # skip a window with a gap or an electrode off
        print(p.head_slot, p.outputs)


device.on_prediction = on_prediction
await device.select_head(2)                      # slot 2: slot 1 holds the open sex head
await device.start()
await device.set_predictions(True)
```

A program can then drive the board's pins from `p.outputs`, as a signal any circuit, robot or project of your own can act on.

## Requests

`device.command(name, arg)` sends any request in [the protocol](https://docs.intomind.com/protocol.html) by name and returns what the answer carries. A refusal raises `intomind.Refused`, with the status number in `status` and its name in `status_name`.

```micropython
await device.command("identify", 5)              # the status light winks for five seconds
await device.command("set_indicator", 2)         # verbose
```

`intomind.protocol` is the protocol on its own, in plain Python, for reading what an answer carries, such as `intomind.protocol.decode_battery(payload)`.

The library's tests read every message the way the published `@intomind/sdk` reads it.

## License

Free software under the GNU Affero General Public License, version 3, with a permission to combine it with MicroPython and the libraries the firmware carries. For a commercial license, write to contact@intomind.com.
