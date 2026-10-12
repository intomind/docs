---
title: The model and heads
description: The neural network on the IntoMind One describes every 4 seconds of EEG with 76 numbers. Collect them, train your own heads, run the heads on the device, and turn the model's tokens back into signal.
---

# The model and heads

The IntoMind One runs a small neural network, an encoder, that reads 4 seconds of signal and describes it with 76 numbers, called an embedding. A head turns an embedding into the numbers you care about. You train heads on your own recordings, and the device runs them.

![The encoder on the device, and the heads around it](/assets/img/model.svg)

## Why it works this way

The encoder was trained on EEG from many people and many studies, so it describes EEG in general. It knows nothing about you or your question. A head is where your question goes: a small set of weights, trained on a laptop in seconds, that reads the embedding and produces up to 32 numbers. The device then runs it on every window.

A head is weights, never code. The device does not run code you send it.

## What ships

Every IntoMind One carries three open heads. Age is built into the model and selected when the device starts. Sex is in slot 1, one of the four slots that are yours. The reconstruction head is built into the model, where the device uses it for the [synthetic signal](/device.html#the-synthetic-signal).

Age and sex show what an embedding carries. They are not useful predictors of either. The heads and how they were measured are published at [github.com/intomind/eeg-foundation-model-heads](https://github.com/intomind/eeg-foundation-model-heads).

## Embeddings from the device

The device sends the encoder's output on request while it streams, in two forms:

- **The embedding**, 76 numbers per window. Heads read it, so train heads on it.
- **The tokens**, 80 vectors per window, one per channel for each fifth of a second. The embedding is their mean, and they turn back into signal.

```python
await device.start()
windows = await device.collect_embeddings(100, form="window")   # about seven minutes
tokens = await device.collect_embeddings(1, form="tokens")      # one window's tokens
```

Each window carries the index and device time of its first sample, so it lines up with your recording, and the identity of the encoder that produced it.

## Training a head

```python
from intomind.model import train_head

head = train_head([w.embedding for w in windows], targets, name="focus",
                  encoder_id=windows[0].encoder_id)
```

`train_head` fits a linear model with a ridge penalty that it chooses from your embeddings, and returns the head exactly as the device runs it. It refuses to fit unless there are more windows than the embedding has numbers. The embeddings you train on are the device's own, quantized as its heads receive them, so a head gives on your computer what it gives on the device.

## Running it on the device

```python
await device.upload_head(head, slot=2, select=True)    # slots 1 to 4 are yours; 1 holds the sex head
device.on_prediction = lambda dev, p: print(p.outputs)
await device.set_predictions(True)
```

The device checks a head's hash and its shape before it stores it. It never checks for a signature of ours, so you can run any head you train. A head records the encoder it was trained on, and the library and the Command Center warn you when it differs from the device's.

Each prediction names the head that made it and the index of the window's first sample, so predictions line up with the signal. It also says whether the window had a gap or an electrode off. The model runs only on time the stream does not need, so it never costs you samples.

The [JavaScript](/javascript.html#run-your-own-head) and [Rust](/rust.html#run-your-own-head) packages upload heads too.

## How often it runs

By default the model describes every window, a new one every 4 seconds. You can ask for one window every so many seconds instead, on a grid that starts with the stream. The device keeps the setting when it is turned off.

```python
interval = await device.model_interval()    # the interval in force, and the shortest the device allows
await device.set_model_interval(60)         # one window a minute; 0 is every window
```

## What the model reads

The model reads the stream: the processing chain's output, or the unfiltered signal when there is no chain. You can point it at the unfiltered signal or at a chain of its own without changing the stream, and every prediction says which it read. The model always works at 500 samples per second, from its own copy of the stream. The stream you receive is never resampled.

## Turning tokens back into signal

The open reconstruction head ships with the Python API and turns each token back into the fifth of a second it came from.

```python
from intomind.model import Reconstructor

reconstruct = Reconstructor.shipped()
window = (await device.collect_embeddings(1, form="tokens"))[0]
signal = reconstruct.from_tokens(window.tokens, channels=4, tokens_per_channel=20)   # (channels, samples)
```

What comes back is what the encoder kept of the window, in the model's normalized units. On windows from studies it was not fitted on, it returns about two thirds of the signal's variance: most of the rhythms below 13 Hz, less of those from 13 to 30 Hz, and little above 30 Hz. Windows with large artifacts do not come back in amplitude.

## The weights

The encoder's weights stay on the device. They arrive only in signed updates from IntoMind, cannot be read over the link, and are not published. Everything you work with is open: the embeddings and tokens the device sends, the heads you train, and the reconstruction head.
