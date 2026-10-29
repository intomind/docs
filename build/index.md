---
title: IntoMind One
description: Documentation for IntoMind One, a four-channel wearable EEG device, and for its open software: the Command Center, the Python API, the SDK for Rust and JavaScript, and the intomind library for MicroPython.
url: https://docs.intomind.com/index.html
---

# IntoMind™ One

IntoMind One is a research grade EEG device that you wear. It streams four channels of your brain's electrical activity to your computer over Bluetooth, and the software that records, analyzes and builds on it is open.

## Start here

| | |
|---|---|
| [The device](https://docs.intomind.com/device.html) | what is in the box, charging, wearing it, the lights, and connecting |
| [Command Center](https://docs.intomind.com/command-center.html) | the app for seeing the signal, recording, and exporting |
| [Python](https://docs.intomind.com/python.html) | the API, for scripts, recordings and analysis |
| [Recordings and files](https://docs.intomind.com/files.html) | what a recording is, what each export holds, and the rule versions follow |
| [Rust](https://docs.intomind.com/rust.html) and [JavaScript](https://docs.intomind.com/javascript.html) | the SDK, for building your own applications |
| [MicroPython](https://docs.intomind.com/micropython.html) | MicroPython for the Raspberry Pi Pico 2 W, for programs that run on the board |
| [The model and heads](https://docs.intomind.com/model.html) | the neural network on the device, and training your own heads |
| [The protocol](https://docs.intomind.com/protocol.html) | the Bluetooth contract, for writing your own client |
| [Safety and care](https://docs.intomind.com/safety.html) | warnings, the battery, and cleaning |
| [Glossary](https://docs.intomind.com/glossary.html) | the terms used on this site |

## How it works

![The signal from the scalp to your computer](https://docs.intomind.com/assets/img/signal-path.svg)

Four electrodes and a reference rest on the scalp. The ADC converts what they pick up into 24-bit samples, at 250, 500 or 1000 samples per second, and the device stamps each sample with its own clock. The device filters the signal through a processing chain you can read and change, and every stream states the chain that produced it. If a sample is lost on the way, the stream says where and how many. Nothing is filled in.

The device also runs a neural network that describes every 4 seconds of signal with 76 numbers. You can train heads on those numbers and run them on the device. In place of the electrodes, a generator on the device can stream a synthetic signal, marked as generated wherever it goes.

## What you need

A computer with Bluetooth Low Energy. The Command Center runs on it and shows its page in your browser. Once installed, it needs no account and no internet connection.

## Open source

The Command Center, the API, the SDK, the `intomind` library for MicroPython and the open heads are free software under the [GNU Affero General Public License, version 3](https://www.gnu.org/licenses/agpl-3.0.html). For a commercial license, write to contact@intomind.com.

| | |
|---|---|
| [github.com/intomind/commandcenter](https://github.com/intomind/commandcenter) | the Command Center |
| [github.com/intomind/api](https://github.com/intomind/api) | the Python API, `pip install 'intomind[analysis]'` |
| [github.com/intomind/sdk](https://github.com/intomind/sdk) | the SDK, `cargo add intomind` and `npm install @intomind/sdk` |
| [github.com/intomind/micropython](https://github.com/intomind/micropython) | MicroPython for the Raspberry Pi Pico 2 W, with the `intomind` library |
| [github.com/intomind/eeg-foundation-model-heads](https://github.com/intomind/eeg-foundation-model-heads) | the open heads for the model on the device |
