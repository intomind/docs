---
title: The device
description: The IntoMind One manual: what is in the box, charging, turning it on, wearing it, the lights, connecting, its name, the synthetic signal, firmware updates, troubleshooting, and specifications.
---

# The device

**IntoMind One (IM-1)**

## What is in the box

- The IntoMind One, assembled and programmed, in its 3D printed enclosure, with its rechargeable battery and comfort strap.
- A T-shirt in the size you chose at checkout.

A charging cable is not included.

## Charging

> **Warning.** To ensure safety, never wear the device or touch its electrodes while USB is plugged in.

Plug a USB-C cable into any USB charger or computer. The charge light shows what the charger is doing. Charging from empty takes about an hour and three quarters, and a full charge streams for about 25 hours.

While USB is plugged in, the device charges and stays connected, but it does not stream from its electrodes. A stream cannot be started, and a stream that is running stops when the cable goes in. The [synthetic signal](#the-synthetic-signal) still streams.

## Turning it on and off

Slide the power switch to turn the device on. The amber power light is lit while the device is on, and your computer can find it.

The battery drains slowly even while the device is off, so charge it before you store it.

## Wearing it

The electrodes must touch skin, not hair. Part the hair where each electrode sits, and press the device down until the electrodes rest on the scalp. The comfort strap holds it in place and lets you place the electrodes anywhere on the head. It should feel firm but not tight.

A noisy channel almost always means poor contact. Lift the device, part the hair again, and press it back down. If every channel is noisy, check the reference electrode.

The Command Center can turn on lead-off detection, which shows which electrodes are in contact with the skin. It passes a very small current through the electrodes, so it stays off until you turn it on.

## The lights

| Light | Color | What it shows |
|---|---|---|
| {{lamp}} Power | amber | lit while the device is on |
| Charge | yellow, magenta or red | lit only while USB is plugged in: yellow while charging, magenta when full, red when no battery is connected |
| Status | amber | what the device is doing, in the patterns below |

The status light has three settings: silent, reserved and verbose. The device ships set to reserved and keeps its setting when it is turned off. The Command Center sets it under the device's settings.

{{light-patterns}}

| Pattern | Meaning | Shown in |
|---|---|---|
| Lit, with a short dark wink once a second | your software asked this device to identify itself | every setting |
| Three blinks, then a pause | the ADC failed its check at power on, so the device cannot record | reserved and verbose |
| Two blinks, then a pause | the battery is below 20 percent, until it reaches 25 percent or USB is plugged in | reserved and verbose |
| Fast blinking | an update is being written | verbose |
| A brief pulse every two seconds | streaming | verbose |
| Steady | connected | verbose |
| A short blink once a second | on, and waiting for a computer | verbose |

When more than one applies, the light shows the one highest in the table.

## Connecting

Turn the device on and connect from the [Command Center](/command-center.html) or your own software. The first time, your computer pairs with the device, with no code to enter. After that it connects without pairing again. The link is encrypted.

The device remembers four computers. When a fifth pairs, it forgets the one used least recently.

## Several devices at once

One computer can stream from two devices at 250 samples per second each. At 500 or 1000 samples per second, stream from one device per computer.

## Its name

The device can carry a name and an adjective that you choose, and every computer and phone that scans for Bluetooth devices sees them with the product's name: Ada's Blue IntoMind One. With only a name it is Ada's IntoMind One, with only an adjective Blue IntoMind One, and with neither IntoMind One. The device keeps them when it is turned off, and a new name appears in scans once the computer that set it disconnects.

The whole name is at most 29 bytes. English letters, digits and spaces take one byte each. Accented letters and other scripts take two to four.

{{name-composer}}

When two devices near your computer have the same name, the software numbers the second one: Ada's IntoMind One 2. The number exists only on your computer.

## The synthetic signal

The device can stream a signal it generates itself, in place of its electrodes, to test software without anyone wearing it and for demonstrations. It runs at 500 samples per second, and every packet and recording of it is marked as generated. The Command Center says so above the trace.

The device runs one neural network at a time. While it generates the signal, it sends no embeddings and no predictions, and it does not start generating while either is on.

The generator draws the encoder's tokens, and the reconstruction head turns them back into signal. Compared with 19,459 windows of real EEG from 37 studies it was not trained on:

| | Synthetic | Real EEG |
|---|---|---|
| A linear classifier on the encoder's embeddings, telling generated from real (0.5 means it cannot tell) | 0.56 | 0.38 to 0.58, between real studies |
| The same classifier, trained and scored on studies the generator never saw | 0.64 | |
| A nonlinear classifier on the same embeddings | 1.00, it always tells them apart | |
| Power spectrum, 1 to 45 Hz | 1.5 dB from real EEG on average | |
| Coherence between channels, 8 to 13 Hz | 0.18 | 0.28 |

The generator was trained with the encoder in the loop, so the first result is partly by design. The signal describes no one and varies less over time than a real person does. Use it to test software, never as data.

## Firmware updates

Firmware updates install over Bluetooth. The device keeps two copies of its firmware, writes an update to the copy it is not running, and runs only firmware signed by IntoMind. If your computer cannot connect after an update, turn the device off and on. If it still cannot connect, turn it off and on once more, and the device returns to the previous firmware.

## If something is wrong

| What you see | What to do |
|---|---|
| It does not appear in a scan | Check that the power light is on. If it is not, charge the device. |
| One channel is noisy | Improve that electrode's contact: lift the device, part the hair, and press it down. |
| Every channel is noisy | Improve the reference electrode's contact. |
| A stream will not start, or stops | Unplug USB. The device does not stream from its electrodes while USB is plugged in. |
| It disconnects | Move the computer closer, and away from other devices on the same radio band. |
| It connects but never answers, or a feature is missing after an update | Remove the device in your computer's Bluetooth settings (on Linux, `bluetoothctl remove` and its address) and connect again. |
| Three blinks | Turn the device off and on. If it happens again, write to support@intomind.com. |
| The Command Center says another program is listening | Another program on this computer is subscribed to the device, so every packet arrives twice. The copies are dropped and the recording is complete. |

## Specifications

| | |
|---|---|
| Channels | 4, with a shared reference |
| Electrodes | five, dry and gold-plated |
| ADC | Texas Instruments ADS1299-4, 24 bits |
| Sample rates | 250, 500 or 1000 per second |
| Gain | 1, 2, 4, 6, 8, 12 or 24 |
| Noise | 0.14 µV root mean square, inputs shorted, at 250 samples per second |
| Timestamps | every sample, from the device's own clock |
| Processing | high-pass, notch and low-pass filters on the device, which you can read and set |
| Model | an encoder that describes each 4-second window with 76 numbers, and four slots for your heads |
| Radio | Raytac MDBT50Q-1MV2 module, Nordic nRF52840 |
| Link | Bluetooth Low Energy, encrypted |
| Battery | rechargeable lithium polymer, charged over USB-C |
| Lights | power, charge and status |
| Enclosure | 3D printed bioplastic, with an adjustable comfort strap |

## What the IntoMind One supports

The [protocol](/protocol.html) covers every IntoMind device, and each device reports which parts it supports.

| Feature | IntoMind One |
|---|---|
| Streaming at three rates and seven gains, the ADC's test signal and shorted inputs, lead-off detection, time sync | yes |
| Battery and charger state | yes |
| Signed firmware updates over Bluetooth | yes |
| The processing chain: read, set, clear, and restore the default | yes |
| The model: embeddings, heads, predictions, and how often it runs | yes |
| The status light: its setting, and identify | yes |
| The ADC's registers, read while not streaming | yes |
| Its name | yes |
| The synthetic signal | yes, at 500 samples per second |
| The bias drive | no |
