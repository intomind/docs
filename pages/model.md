# The model and heads

The device carries a small neural network. It reads four seconds of your
signal and produces seventy six numbers that describe it. Those numbers
are called an embedding, and a head is what turns them into something you
care about.

## Why it works this way

The encoder was trained on a large amount of EEG from many people and many
recordings, so it has learned what EEG generally looks like. It has not
learned anything about you, and it has not been told what you want to
know. That is deliberate: the encoder is the expensive part and it ships
once, while what you want to know is yours and changes.

A head is a small set of weights that reads the embedding and produces up
to thirty two numbers. You train it on your own recordings, on a laptop,
in seconds. Then you upload it to the device, and the device produces
those numbers by itself, four seconds at a time, without a computer
attached.

A head is weights and never code. A device will not run code you send it.

## What ships

The device ships with three open heads on board. Age is built into the
weights: it is slot 0, selected whenever the device powers on, and it
changes only with a weights update. Sex is in slot 1, one of the four slots
that are yours to fill, replace, or empty. The reconstruction head is in
the weights too, where the device uses it to make its generated signal.

Age and sex show what the embedding carries. They are not useful
predictors of either. The heads that matter are the ones you train on your
own recordings, for your own question.

## Open heads

We publish these heads, each with what it was measured to do, at
[github.com/intomind/eeg-foundation-model-heads](https://github.com/intomind/eeg-foundation-model-heads).
A head names the encoder it was trained for, and a device reports the
encoder it runs.

## Embeddings from the device

The encoder runs on the device. Ask, and the device sends its output for
each window while it streams, in two forms:

- **the window embedding**, the seventy six numbers a head consumes, one
  vector per window. This is what you train heads on.
- **the tokens**, the eighty vectors that the window embedding is the mean
  of, one per channel per fifth of a second. This is what generation
  starts from.

```python
await device.start()
windows = await device.collect_embeddings(100, form="window")  # about seven minutes
tokens = await device.collect_embeddings(1, form="tokens")     # one window's tokens
```

Each whole window carries the sample index and device time of its first
sample, the encoder that produced it, and what the window was taken from,
so it lines up against your recording. Both forms are quantized exactly
as the device's heads receive them.

## Training a head

```python
from intomind.model import train_head

blob = train_head([w.embedding for w in windows], targets, name="focus",
                  encoder_id=windows[0].encoder_id)
```

`train_head` fits the head and returns exactly the bytes the device will
run. It refuses to fit unless there are more windows than the embedding
has numbers, because a head fitted on fewer describes the noise in one
recording rather than anything about you.

The fit is least squares with a ridge term, and the ridge is chosen from
your embeddings unless you pass one. The encoder's last normalization
leaves one direction of the embedding with almost no variance, and a fixed
small ridge lets the fit spend most of a row's integer range on that
direction. The chosen ridge removes it and leaves the rest of the fit
essentially untouched, so the head the device runs scores what the float
fit scored.

A head records the encoder whose embeddings it was trained on, when you
say which. Every window from the device names its encoder, so the example
above passes that along.

## Uploading it

```python
head_id = await device.upload_head(blob, slot=2, select=True)
await device.set_predictions(True)

device.on_prediction = lambda dev, p: print(p.outputs, p.head_id)
```

There are four slots for your heads, 1 to 4. A unit ships with the open
sex head in slot 1, so this example uses slot 2. A head carries its own
hash, the device checks it
before storing it, and every prediction the device sends carries the hash
of the head that produced it. A recording of predictions therefore always
says which head made them, which matters the first time you have two.

A head is yours. It is checked for its own hash and for its shape, never
for a signature of ours, so nothing stops you putting your own model on
your own device. Our firmware is signed and the device refuses anything
else in its place. Your head is not, and the device runs it.

A head trained beside a different encoder than the one on the device is
stored and runs like any other. The library warns you when you upload
one, and the Command Center marks it, because its outputs were learned
from another encoder's view of the signal and may not mean what its name
says. Whether it still means something is yours to judge.

The Rust and JavaScript packages do the same thing without a Python
runtime. Both hand back a state machine rather than doing the input and
output themselves, so it works over whatever Bluetooth stack you have.

```javascript
import { Transfer, requestAndConnect } from "@intomind/sdk";

const link = await requestAndConnect();
const transfer = Transfer.head(link.session, 1, blob);
await link.transfer(transfer, blob, ({ taken, total }) => report(taken, total));
await link.send(link.session.selectHead(1));
await link.send(link.session.setPredictions(true));
```

## What comes back

Each prediction covers one window and says where that window started, in
the same sample index the raw stream uses, so predictions line up with
signal exactly. It also says whether the window had a gap in it, whether
an electrode was off, and whether the device reduced its own rate to stay
inside its power budget.

The model never runs at the cost of the stream: acquisition has priority,
and the model gets what is left.

## How often it runs

You choose how often the model describes a window. By default it
describes every window it can, and the device reports how long one pass
takes. Or ask for one window every so many seconds, on a grid that starts
with the stream, which is what a recording that wants equal spacing needs.
A longer interval leaves the processor idle between passes. The device
keeps the setting across power cycles, and it states its own minimum.

```python
interval = await device.model_interval()     # the interval in force, and the device's minimum
await device.set_model_interval(60)          # one window a minute; 0 is every window it can
```

## What the model reads

The model follows the stream: the chain's output when a chain is on, the
natural signal otherwise. A predictions session may point it elsewhere,
at the natural signal or at a chain of its own, without touching the
stream, and every prediction says where its window came from. The model
declares the signal classes it can take, and a chain it cannot take is
refused; nothing about that is fixed in the device.

## What you fit is what runs

A head's sums are exact integers on your computer and on the device, and
only its final scale is a floating point multiplication, so a head gives
on your computer what it gives on the device. The embeddings you train on
are the device's own, quantized as its heads receive them. What you
measure while training is what the device does, not an approximation of
it.

## Generating

The encoder has a companion that turns each token back into the fifth of
a second it came from: the reconstruction head, an open file you can
inspect and change. It ships with the library. Generation is that head
run on tokens, and the tokens come from the device.

```python
from intomind.model import Reconstructor

back = Reconstructor.shipped()
w = (await device.collect_embeddings(1, form="tokens"))[0]
signal = back.from_tokens(w.tokens, channels=4, tokens_per_channel=20)   # (channels, samples)
```

What comes back is in the model's own normalized units, and it is not the
window. It is what the model believes the window was. On a typical window
from recordings it was never fitted on, it returns about two thirds of the
variance: most of the slow rhythms below 13 Hz, less of the faster ones,
and little above 30 Hz. The difference is what the embedding could not
carry, and looking
at that difference is the point: it shows you what the model is paying
attention to and what it is throwing away. It reconstructs structure and
it cannot reconstruct noise.

Synthetic signal is the same call on tokens you made up: mix two windows'
tokens, move a token towards another, or sample around one, then
reconstruct.

This is not a head. A head produces a few numbers for you to act on. This
produces signal, and it exists so the embedding is inspectable rather
than opaque.

## A synthetic signal from the device

The device can also generate a signal itself and stream it in place of
its electrodes, drawing tokens from a small model trained on the corpus
and turning them back into signal with the same reconstruction head. It is
marked as generated wherever it goes. The device runs one model at a
time, so while it generates, the encoder does not run: there are no
embeddings and no predictions until it stops. What it is for, how close it
comes to real EEG and where it falls short are on
[the device page](device.html).

## Rates

The model has one native rate, five hundred samples per second. The device
keeps its own copy of the stream on that grid, so you can record at any
rate the device offers and the model behaves identically. The raw stream
is never resampled.

## Weights

The encoder's weights stay on the device. They reach it only as signed
updates from IntoMind, they cannot be read back over the link, and they
are not published. Everything you work with is the model's output: the
embeddings the device sends, the heads you train on them, and the
reconstruction head, all of them open. How the weights were made and what
they were measured to do is in our paper, linked here once it is posted.

Your device runs the model, and your computer trains heads and generates
signal, without the weights ever leaving it.
