---
title: Python
description: The intomind Python API for the IntoMind One: install, connect, stream, set up the device, collect embeddings and run heads, read recordings, export, and analyze.
url: https://docs.intomind.com/python.html
---

# Python

The `intomind` package is the Python API for the IntoMind One. It connects to the device, streams its signal, and reads, exports and analyzes recordings. The [Command Center](https://docs.intomind.com/command-center.html) is built on it.

```sh
pip install 'intomind[analysis]'
```

It needs Python 3.11 or newer. The `analysis` extra installs SciPy, which reading recordings, exporting and the analyses need. For MATLAB export, install `'intomind[analysis,mat]'`.

```python
import asyncio

from intomind.client import display_names, scan
from intomind.session import Session


async def main():
    found = await scan()                       # every device that answered
    names = display_names(found)               # address to name, numbered when two share one
    device = next(d for d in found if names[d.address] == "Ada's IntoMind One")

    session = Session()
    await session.connect(device)              # only the device you picked
    device = session.devices[0]

    device.on_sample = lambda dev, sample: print(sample.index, sample.uv)
    await device.start()
    await asyncio.sleep(5)
    await device.stop()
    await session.close()


asyncio.run(main())
```

Each sample carries the device's index (`sample.index`), the device time at which it was converted (`sample.device_time`), that time on your computer's clock (`sample.host_time`), and one value per channel in microvolts (`sample.uv`).

The first connection pairs the device with your computer, and later connections reuse the pairing. On Linux the library answers the pairing request itself, so no settings window is needed and a computer without a screen works. If a connection fails because the link could not be secured, the error says what to do.

## What the device reports

The library holds no table of hardware. What a device can do is what it reports, and a request for anything else is refused before it is sent, with an error that names the missing capability.

```python
device.info.channels          # 4
device.info.adc_bits          # 24
device.info.rates             # the sample rates it offers
device.can("model")           # True when it reports that capability
```

## Processing on the device

The device filters its signal through a chain you can read and change, and only the chain's output streams. The device refuses changes while it streams: stop, set, and start again.

```python
from intomind import protocol

state = await device.pipeline()                        # the chain in force
await device.set_pipeline([protocol.highpass(0.5),
                           *protocol.mains_bands(60, 500),  # 60 Hz and the harmonics 500 per second can carry
                           protocol.lowpass()])        # the automatic corner
await device.restore_pipeline_default()
await device.clear_pipeline()                          # no processing
```

A chain that cannot run at the device's rate is refused, with the reason, before anything is sent.

## The light, the name, and the registers

```python
await device.set_indicator("verbose")       # "silent", "reserved" or "verbose"
await device.identify(5)                    # the status light winks for five seconds

await device.set_name("Ada", "Blue")        # refused if the whole name would not fit
protocol.compose_name("Ada", "Blue")        # "Ada's Blue IntoMind One"

regs = await device.converter_registers()   # the ADC's registers, while not streaming
regs.describe()                             # its settings, in words
```

## The synthetic signal

```python
await device.set_mode("synthetic")          # the generator, at 500 samples per second
await device.set_mode("normal")             # back to the electrodes
```

Turn embeddings and predictions off first, because the device runs one neural network at a time. Every generated sample has `sample.synthetic` set. See [the device](https://docs.intomind.com/device.html#the-synthetic-signal) for what the signal is.

## The model

This example collects four minutes of embeddings with eyes open and four with eyes closed, trains a head that tells them apart, and runs it on the device.

```python
from intomind.model import train_head

await device.start()
opened = await device.collect_embeddings(60, form="window")    # 60 windows, 4 minutes, eyes open
closed = await device.collect_embeddings(60, form="window")    # eyes closed

head = train_head([w.embedding for w in opened + closed],
                  [0] * len(opened) + [1] * len(closed),
                  name="eyes closed", encoder_id=opened[0].encoder_id)

await device.upload_head(head, slot=2, select=True)
device.on_prediction = lambda dev, p: print(p.outputs)
await device.set_predictions(True)
```

[The model and heads](https://docs.intomind.com/model.html) explains embeddings, heads, and how often the model runs.

## Gaps and repeated packets

```python
from intomind import analysis

capture = analysis.load("my-recording")    # checks the checksums first
capture.gap_before                         # one flag per sample: True where samples were lost before it
capture.meta["synthetic"]                  # True when the device generated the signal
```

The device numbers every sample, so a loss has an exact count. When the device restarts its count, the library reports a break of unknown length, never a count.

When another program on the same computer listens to the device, every packet arrives twice. The library drops the copies and counts them in `device.duplicates`.

## Where recordings go

```python
from intomind import provenance

provenance.use_captures_dir("~/study/captures")
provenance.use_site({"mains_hz": 60, "electrode_montage": "four over the forehead"})
```

Recordings go to `~/.local/share/intomind/captures` unless `INTOMIND_CAPTURES` or `use_captures_dir` names another folder. `use_site` records facts about where you record. Anything you do not declare is recorded as unknown.

## Exports

```python
from intomind import export

export.export("my-recording", "bdf")       # also "edf", "npz", "csv", "tsv" and "mat"
```

Each export reports whether every value came out exactly as recorded, and if not, the largest error in microvolts. A recording whose checksums do not match is refused.

In BDF and EDF, every sample stays at the time it was recorded. Where samples were lost, the file holds the lowest value it can store for each of them, under a `BAD_ACQ_SKIP` annotation that MNE reads as its own, so MNE leaves the hole out of filtering and returns it as NaN when asked. These formats store whole numbers, so NaN cannot be written, and zero would stretch every signal's range and make every recorded sample in an EDF file less precise. `export.export` reports how many samples it filled in `samples_filled`.

## Analyses

```python
analysis.summary("my-recording")           # offset, noise, band power, spectral slope
analysis.psd_curve("my-recording")         # the power spectrum of every channel
analysis.berger("my-recording")            # alpha with eyes closed against eyes open
```

## Other hardware

An adapter, in a package of its own, adds methods under `device.extra` for the devices it claims. A device without one behaves as documented here. See `adapters.py` in the [repository](https://github.com/intomind/api).

## License

Free software under the GNU Affero General Public License, version 3. For a commercial license, write to contact@intomind.com.
