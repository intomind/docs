# Python

```
pip install intomind
```

The instrument library: the link to a device, the protocol, the
recording, its provenance, the exports, and the analyses that read it
back.

```python
from intomind.client import display_names, scan
from intomind.session import Session

found = await scan()                   # every device that answered, as heard
labels = display_names(found)          # each one's name, numbered when two share one
chosen = next(d for d in found if labels[d.address] == "Ada's IntoMind One")
s = Session()
await s.connect(chosen)                # only the one picked
device = s.devices[0]

device.on_sample = lambda dev, sample: print(sample.uv)
await device.start()
```

Nothing connects that was not chosen. With two devices in a room, the
first to answer a scan is not necessarily the one you meant.

The first connection pairs the device with the computer, and the pairing
is kept, so later connections do not pair again. On Linux the library
answers the pairing itself, so no settings window is needed and a headless
machine works. Pairing from the system's Bluetooth settings first works
too: the library finds the device paired and asks nothing, and it finds a
device the computer is already connected to, which does not advertise and
no scan alone could see. The library is
never the system's default pairing agent, so the rest of your Bluetooth
behaves as before. If a connection fails with a message that the link
could not be secured, the remedy is in the message.

## The device answers for itself

Nothing in the library holds a table of hardware. What a device can do is
what the device reports.

```python
device.info.channels          # what it said
device.info.adc_bits          # what it said
device.info.rates             # what it said
device.can("model")           # a capability bit, not a version number
device.profile()              # the controls to offer, composed from the above
```

Asking a device for something it does not claim is refused before
anything reaches the wire, with a message that says which capability is
missing.

## Processing on the device

A device that claims the processing chain preprocesses its own signal.
Filters come first: a high-pass, a low-pass, and any number of notch bands,
on from the first use with the device's own default. When a chain is in
force only its output streams, and the chain is readable at any time, so a
recording says exactly what produced its samples. There is no raw-or-filtered
flag anywhere, because a flag says nothing about what a signal is.

```python
from intomind import protocol

device.pipeline()                       # the chain in force, and whose it is
device.set_pipeline([protocol.highpass(0.5),
                     *protocol.mains_bands(50, 500),  # the bands 500/s can carry
                     protocol.lowpass()])   # automatic corner for the rate
device.restore_pipeline_default()
device.clear_pipeline()                 # the natural signal
device.pipeline_at_start                # what the last stream was made by
protocol.describe_chain(device.pipeline().stages, 500)
```

The rules a chain must meet are the device's, restated in the library, so
a chain that cannot run at the device's rate is refused in words before
anything is sent. The device refuses a change while streaming: stop, set,
start. The model follows the stream unless you point it elsewhere with
`device.set_prediction_input`, at the natural signal or at a chain of its
own, without touching the stream.

## The light, and the converter's registers

A device that claims the status light lets you choose how much it says.
Silent shows nothing. Reserved, the default, shows low battery and a
failed start-up check. Verbose adds waiting, connected, streaming, and
update in progress. The device keeps the setting across power cycles, and
it can blink on request so you know which device you are talking to.

```python
await device.indicator()                 # "reserved"
await device.set_indicator("verbose")
await device.identify(5)                 # the light winks for five seconds
```

A device that claims register reading lets you see how its analog
converter is set, raw and in words, for debugging. Read only, and only
while not streaming.

```python
regs = await device.converter_registers()
regs.describe()      # data rate, gain and input per channel, bias, lead-off ...
```

## Its name

A device that claims a name keeps two parts you set, a name and an
adjective, and advertises them composed with the product's name. The
whole is at most 29 bytes, which is what a scan list shows, so it is never
cut short.

```python
from intomind import protocol

await device.get_name()                     # ("Ada", "Blue")
await device.set_name("Ada", "Blue")        # refused in words if it would not fit
protocol.compose_name("Ada", "Blue")        # "Ada's Blue IntoMind One"
protocol.name_fits("Beatrice", "Purple")    # False: 30 bytes
```

Two devices in one list may share a name. `display_names` numbers the
later ones, and the number is your computer's, never the device's.

```python
from intomind.client import display_names, scan

labels = display_names(await scan())        # address to label, "Ada's IntoMind One 2" for a twin
```

## A synthetic signal

A device that claims it can stream a signal it generates itself, in place
of its electrodes, at 500 samples per second. Every sample says it was
generated, and so does a recording made from it. The device runs one
model at a time, so turn predictions and embeddings off first. While it
generates, it refuses both.

```python
await device.set_mode("synthetic")          # the converter off, the generator on
device.on_sample = lambda dev, s: s.synthetic   # True for every generated sample
await device.start()
await device.stop()
await device.set_mode("normal")             # back to the electrodes
```

What it is for and how close it comes to real EEG are on
[the device page](device.html).

## Embeddings and generation

A device that claims embeddings sends its encoder's output for each window
while it streams, on request: the window embedding a head consumes, the
tokens that generation starts from, or both. No head needs to be selected.

```python
await device.start()
windows = await device.collect_embeddings(100, form="window")   # about seven minutes
one = (await device.collect_embeddings(1, form="tokens"))[0]
device.on_embedding = lambda dev, w: print(w.index, len(w.embedding or []))
await device.set_embeddings("both")      # or "off"
```

Each whole window carries the sample index and device time of its first
sample, the encoder that produced it, and what it was taken from. What
you do with them is in [the model and heads](model.html): train a head,
or turn tokens back into signal with the open reconstruction head, which
ships with the library as `Reconstructor.shipped()`.

How often the model describes a window is yours to set: every window it
can, which is the default, or one every so many seconds.

```python
interval = await device.model_interval()    # the interval in force, and the device's minimum
await device.set_model_interval(60)         # one window a minute; 0 is every window it can
```

## Gaps are never papered over

Every sample carries the device's own index and the device time of its own
conversion. When something is missed, the recording says so.

```python
capture = analysis.load("my-recording")
capture.repairs               # anything load had to correct, in words
capture.gap_before            # one flag per sample
capture.meta["synthetic"]     # true when the device generated the signal
```

A forward step in the index is a loss with an exact count. A step that is
not forward is a break whose extent is not a number, and the library says
unknown rather than returning a count that would be a fiction.

A packet that arrives twice is dropped and counted, never recorded twice.
It happens when another program on the same computer listens to the device,
because the system sends each notification once per listener.

```python
device.duplicates           # packets that arrived twice and were dropped
device.another_listener     # another program is listening right now
```

## Recording

```python
from intomind import provenance
provenance.use_captures_dir("~/study/captures")
provenance.use_site({"mains_hz": 50,
                     "electrode_montage": "four over the forehead"})
```

Anything you do not declare is recorded as unknown. Nothing is guessed.

## Exports

```python
from intomind import export

export.FORMATS                # the six
export.export("my-recording", "bdf")
```

Every exporter refuses a recording that does not verify against its own
checksums.

## Analyses

```python
from intomind import analysis

analysis.summary("my-recording")
analysis.psd_curve("my-recording")
analysis.berger("my-recording")     # eyes closed against eyes open
```

The analyses need scipy, which is an optional extra:
`pip install 'intomind[analysis]'`.

## The model

See [the model and heads](model.html).

## Hardware this library was not written for

An adapter claims a device and hangs its own methods off `device.extra`.
The library never calls into one, so a device with no adapter behaves
exactly as documented. See `adapters.py`.
