---
title: Glossary
description: The terms used in the IntoMind One documentation, from ADC and channel to embedding, head, token and window.
---

# Glossary

| Term | Meaning |
|---|---|
| ADC | The analog-to-digital converter, which turns the electrodes' voltages into numbers. The IntoMind One uses a Texas Instruments ADS1299-4. |
| API | The Python package `intomind`, for scripts, recordings and analysis. |
| Capability | A feature a device reports that it supports. Software asks a device only for what it reports. |
| Channel | One electrode, measured against the reference. The IntoMind One has four. |
| Command Center | The app for using the device from your computer, in your browser. |
| Device time | The device's own clock, which stamps every sample. Software maps it onto your computer's clock. |
| Embedding | The 76 numbers the encoder produces for each window. Heads read them. |
| Encoder | The neural network on the device that produces embeddings and tokens. |
| Filter | A high-pass filter removes slow drift, a low-pass filter removes fast content, and a notch filter removes a narrow band, such as the mains frequency. |
| Gain | How much the ADC amplifies the signal before converting it, from 1 to 24. |
| Gap | A place in a stream where samples were lost. The stream says where and how many. |
| Generator | The small model on the device that produces the synthetic signal. |
| Head | A small set of weights that turns an embedding into up to 32 numbers. You train heads and run them on the device. |
| Lead-off detection | A check that shows which electrodes touch the skin, by passing a very small current through them. |
| Mains frequency | The frequency of household electricity, 50 or 60 Hz, which every EEG picks up. |
| Pairing | The first connection between a computer and the device, which sets up the encryption for every later one. |
| Placeholder | A value written in a BDF or EDF file where a sample was lost, repeating the last recorded value, under the label that marks the hole. |
| Processing chain | The filters the device applies to its signal before streaming it. Every stream states its chain. |
| Protocol | The contract for the Bluetooth messages between an IntoMind device and any software. |
| Reconstruction head | The open head that turns tokens back into signal. |
| Recording | The samples, the manifest, the markers and the checksums that one capture session wrote, kept together under one name. |
| Reference | The electrode every channel is measured against. |
| Sample | One measurement of every channel at one moment. |
| Sample rate | How many samples the device takes per second: 250, 500 or 1000. |
| SDK | The Rust crates and the JavaScript package for building your own applications. |
| Slot | One of four places on the device for a head you upload. |
| Synthetic signal | A signal the device generates in place of its electrodes, marked as generated wherever it goes. |
| Token | One of the 80 vectors the encoder produces for each window, one per channel for each fifth of a second. |
| Web Bluetooth | The browser feature that lets a web page connect to a Bluetooth device. |
| Window | Four seconds of signal, the span the model describes at once. |
| µV | A microvolt, one millionth of a volt. EEG is measured in microvolts. |
