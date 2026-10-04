# IntoMind BLE Protocol v1.3

Status: as built in firmware 1.3.5, 2026-09-29. Firmware 1.3.3 refused a
rate change on the device's default chain when the old chain held a band
the new rate cannot carry, for example 500 to 250 samples a second.
Firmware 1.3.4 accepts it and recomposes the default, as section 16.3 of
1.1 says. It also answers status 1 before status 3 for a rate the synthetic
signal cannot run at while streaming, as the precedence in 1.1 requires.
Firmware 1.3.5 changes nothing a host can see. Firmware 1.3.6 places each
notch's null at the middle of its band, runs each notch as two sections,
and adds both mains' third harmonics to the default chain, as section 16.3
of 1.1 now says. It supersedes 1.2 by addition only, under the rules of
section 0 of 1.1: a 1.2 host works against a 1.3 device, and a 1.3 host reads a 1.2
device's version and asks it nothing new.

What 1.3 adds:

- **Model cadence** (section 20): the model computes whenever it has a
  window and someone wants the result, with no rest imposed by the device.
  The host chooses which windows: every window the device can, or one
  every T seconds on a fixed grid. The device declares how long a pass
  takes. The setting is kept across power cycles. Capability bit 15.
- **Heads** (section 21): a statement, no new number. A head is checked
  for shape and integrity and nothing else; the device never judges what
  a head predicts or which weights it was trained beside.
- **Synthetic signal** (section 22): a stream mode in which the converter
  is off and the device generates an EEG-like signal, drawing its
  encoder's tokens from a generator and turning them back into signal with
  the open decoder for that encoder, and streams it as its own packet type
  so it can never pass for a measurement. The device runs one model at a
  time: while it generates, the foundation model does not run. Capability
  bit 16.
- **Weights update behavior** (section 23): the model stops while its
  weights are being replaced, and the restart that activation asks for
  puts the new weights in force, verified at boot as every image is. One
  new model state.
- **The device's name** (section 24): "IntoMind One", with a name and an
  adjective a user sets and the device keeps, composed so the whole name
  always fits what a scan list can show. Collisions are numbered by the
  host, never by the device. Capability bit 17.
- **Heads that say what they were trained beside** (section 21): a head
  file may carry the id of the encoder whose embeddings it was trained on;
  the device stores and reports it and never judges it, and a host warns,
  without blocking, when it is not the loaded encoder's.
- Four control opcodes, one new SET_MODE value, one packet type, one model
  state, one head state, one input source, five bytes appended to
  GET_MODEL_INFO, four bytes appended to Device Info, a trailer on
  LIST_HEADS, one head format version; three rows in the power-on defaults;
  conformance vectors for every new message.

Nothing already defined in 1.0, 1.1, or 1.2 changes meaning, size, or
number. One 1.2 flag bit is stated more precisely (section 20.3).

## Numbers assigned by 1.3

| Kind | Number | Meaning |
|---|---|---|
| Capability bit | 15 | model cadence, section 20 |
| Capability bit | 16 | synthetic signal, section 22; bit 0 of the second word |
| Capability bit | 17 | the device's name, section 24; bit 1 of the second word |
| Device Info bytes 76..79 | appended | u32, capability bits 16 to 47; `info_len` reads 80 |
| Head format version | 2 | a 40 byte header: the 32 of format 1, then the encoder id, section 21 |
| LIST_HEADS trailer | appended | one 8 byte encoder id per record, after the records, section 21. Withdrawn in 1.4, section 26 of 1.4 |
| Control opcode | 0x88 | SET_MODEL_INTERVAL |
| Control opcode | 0x89 | GET_MODEL_INTERVAL |
| Control opcode | 0x47 | GET_NAME |
| Control opcode | 0x48 | SET_NAME |
| SET_MODE value | 3 | synthetic, section 22 |
| Packet type | 0x04 | synthetic data, section 22 |
| Model state | 3 | updating, section 23 |
| Head state | 3 | width mismatch, section 21 |
| Input source | 3 | synthetic, section 22 |
| GET_MODEL_INFO bytes 17..21 | appended | pass time, interval in force, generator present, section 20.2 |

None of these collides with a number in use or reserved (section 14 of
1.1, the numbers of 1.2). The capability field of Device Info is sixteen
bits wide, so bits 16 and up live in a second word appended at offset 76;
a 1.2 host reads 76 bytes and never sees it, and the contract numbers the
bits straight through.

## 20. Model cadence

A device that sets capability bit 15 runs its model with no rest of its
own: whenever a window is complete and a host has asked for embeddings or
predictions, the next pass starts. How much of the processor and the
battery the model takes is the host's choice, made with the setting below,
and never the device's.

### 20.1 The interval

```
SET_MODEL_INTERVAL   0x88   argument u16 seconds, little-endian
                            0     every window the device can: whenever the model is
                                  free it takes the newest complete window
                            T > 0 one window every T seconds: the windows that start at
                                  sample n × T × rate from the epoch, for n = 0, 1, 2 ...
  response:                 status only. A T below the device's minimum answers status 1
                            and changes nothing. On a device without bit 15, status 2.

GET_MODEL_INTERVAL   0x89   no argument
  response:                 status, then u16 interval in force, u16 minimum
```

The minimum is the smallest T the device can keep: the larger of the
window length and the pass time, in whole seconds, rounded up. On the
IntoMind One with the launch model it is 4, which is every window, so 0 and
4 describe the same windows there.

With interval 0 the device describes every window when its pass is shorter
than the window, and otherwise as many as it can, each the newest complete
one. With T the described windows fall on a grid a host knows in advance,
which is what a recording that wants equal spacing asks for, and it is the
host's lever on battery: a device asked for one window a minute computes
for one pass a minute.

The setting takes effect at the next window. It is kept across power
cycles (section 13). It does not start the model: embeddings or
predictions must still be asked for.

### 20.2 What the device declares

`GET_MODEL_INFO` gains five bytes, appended at offset 17:

```
offset type   field
17     u16    pass_ms          wall time of the last pass, milliseconds; 0 before the first
19     u16    interval_s       the interval in force, as SET_MODEL_INTERVAL set it
21     u8     generator        bit0 the device holds a decoder and a generator that belong to
                               its encoder and offers synthetic signal (section 22); other
                               bits zero
```

A 1.2 host never reads them; a 1.3 host reading a 1.2 device sees the
message end at 17 bytes and knows the device paces itself.

### 20.3 The skipped-windows bit, stated precisely

Bit 1 of the embedding flags (section 19.2) and of the prediction flags
(section 10) is set on a window when at least one window between it and
the previous described window went undescribed, and clear otherwise, and
clear on the first window described after a start. That is what 1.2 says
in fewer words; it is restated because the 1.2 firmware set it on other
grounds. Every described window still carries its first sample's index
and device time, so a host can derive coverage without the bit.

## 21. Heads: what the device checks

Section 11 stands. On FINISH a head is checked for magic, version, kind,
`in_dim` against the loaded encoder's width, `out_dim`, length, and hash,
and for nothing else. A head names no weights and the device asks none of
it: which embeddings it was trained on, and whether what it predicts is
useful, are the user's to judge. A head whose `in_dim` does not match the
loaded encoder cannot be computed and is not stored, and that is the only
sense in which a head is ever refused.

After a weights change (section 23) a stored head whose `in_dim` no longer
matches the loaded encoder is listed by LIST_HEADS with head state 3,
width mismatch, is never run, and is not removed; it runs again if weights
of its width return. A 1.2 host shows the state's number.

### 21.1 What a head says about itself, and what a host does with it

Head format 2 is format 1 with eight bytes appended to the header: the id
of the encoder whose embeddings the head was trained on, all zero when the
trainer did not say. The hash covers it as it covers the rest. The device
accepts either format, stores what it is given, and reports each stored
head's encoder id in a trailer to LIST_HEADS, one id per record after the
records, so a 1.2 host's parse of the records is undisturbed. The device
never compares it with anything.

The trailer is withdrawn in 1.4. With it, an IntoMind One's answer is 194
bytes, longer than any answer may be, so no device sent it. From 1.4 the
ids are in a request of their own, LIST_HEAD_ENCODERS (section 26 of 1.4).

A host that uploads or lists a head whose encoder id is neither zero nor
the loaded encoder's tells the user so and carries on: the head is stored,
selected, and run exactly as any other. Whether a head trained beside one
encoder means anything beside another is the user's question, and this is
the information to ask it with. Our training tools write format 2 with the
id of the encoder that produced the embeddings.

## 22. Synthetic signal

A device that sets capability bit 16 holds, beside its encoder, a decoder
that turns the encoder's tokens back into signal (the open reconstruction
head for that encoder) and a generator, a small recurrent model over the
encoder's token space trained on the corpus. The three travel together in
the weights image, each named by its hash, and the device sets bit 16 only
when the generator names the encoder and the decoder it was trained
beside. In synthetic mode the converter is not driven. The device draws
each channel's next token from the generator, one fifth of a second at a
time, turns it into samples with the decoder, adds noise shaped by two
fixed filters for what the decoder does not return, and streams the result
at the stream's channel count with the stream's own timestamps, indices,
and packet cadence. Nothing downstream of the converter is different: the
chain, the buffer, gaps and packets run as they do on a measured signal.
The foundation model does not run beside the generator (22.4).

### 22.1 Entering and leaving

```
SET_MODE   0x20   gains value 3: synthetic
  Refused with 3 while streaming, as every mode is. Refused with 2 on a device
  without capability bit 16. Refused with 1 unless the rate is 500 samples a
  second, the rate the generator runs at. Refused with 3 while predictions
  are on or embeddings are asked for (22.4). Not kept across power cycles: a
  device powers on in mode 0.
```

The status message's mode field reads 3 while the mode is in force. While
it is, SET_RATE to any rate but 500 answers status 1 and changes nothing,
and SET_MODE with a converter mode, 0, 1, or 2, leaves it.

### 22.2 The packet

Synthetic samples are streamed as packet type 0x04 with exactly the layout
of type 0x01 (section 5): the same header, the same sample encoding, the
same flags and mode bits. A host decodes it with the code it has for 0x01
and knows every sample in it was generated. A 1.2 host, whose decoder
refuses an unknown packet type, never stores one.

Samples are in converter counts, as the device would have measured a
signal of the amplitude the device page states, with the gain field
filled in as usual, so a host scales them the way it scales everything.

A slice the generator has not finished when its samples are due is never
repeated or invented: the stream's index moves past it, and a host sees
the gap as it sees any other.

### 22.3 What it is and is not

The synthetic signal reproduces what the generator learned: the corpus's
power spectrum, band powers, and channel correlations, and the way one
fifth of a second follows the last. It contains no events, because a decoder driven by
statistics does not make blinks, spindles, or spikes. Its purpose is
a stream with the device's real timing that needs no wearer: for building
and testing software against the device, for demonstrations, and for
sharing sessions that hold no one's brain data. What it matches and how
well is measured and stated on the device page. Its realism is a property
of the generator, which travels in the weights image and changes only
with a signed weights update.

### 22.4 One model at a time

The generator and the foundation model are two models, and a device runs
one of them at a time. SET_MODE 3 is refused with status 3 while
predictions are on or embeddings are asked for. While the mode holds,
SET_PREDICTIONS on and SET_EMBEDDINGS with any form but off are refused
with status 3, and off is always accepted. A pass of the foundation model
begun before the mode was entered stops at its next step and its result is
never sent. Only the generator excludes the converter: reconstructing
signal from the tokens of acquired signal needs the converter and the
foundation model, and not the generator. Input source 3, synthetic, stays
defined for a reader, and a device that runs one model at a time never
sends it.

Not in 1.3: seeding the generator from live signal (the device embedding
what it acquires and continuing from those tokens), and a host-supplied
generator. Both are additions when wanted.

## 23. Weights update behavior

The weights partition is single and is written in place, so from the first
byte of a transfer the running model's weights are no longer whole. While a
weights transfer (section 9, target weights) is in progress the model is
therefore stopped before anything is written: GET_MODEL_INFO reports model
state 3, updating; embeddings and predictions pause; the stream is
unaffected. Activation of a verified weights image restarts the device, as
it always has, and the restart is what puts the new weights in force: they
are verified at boot as every image is, and the device comes back ready
with the new encoder's identity and width. A transfer that is aborted, or
fails to verify, leaves the model as it finds it: ready with the old
weights if nothing was written to the partition yet, and otherwise state 1,
no weights, until a restart puts verified weights in force.

A host re-reads GET_MODEL_INFO after any weights transfer. Heads are
handled as section 21 says.

## 24. The device's name

A device that sets capability bit 17 composes its Bluetooth name from two
strings a host may set, a name and an adjective, both kept across power
cycles and both empty from the factory. The composed name is, in order and
separated by single spaces:

- the name followed by `'s`, when a name is set;
- the adjective, when set;
- the product name, which for the IntoMind One is `IntoMind One`.

So a device reads `Ada's Blue IntoMind One`, `Blue IntoMind One`,
`Ada's IntoMind One`, or `IntoMind One`. A 1.2 device advertised
`IntoMind-1-` and four hex digits; that form is gone. A host recognizes a
device by the service identifier it advertises, never by its name, as it
already did.

### 24.1 The whole name always fits

The composed name is the device's Bluetooth device name and its complete
local name in the air. A scan response carries at most 29 bytes of name,
which is what every scan list on every phone and computer can show, so the
composed name is limited to 29 bytes of UTF-8. The limit is on the result,
not on the parts: a long name leaves less room for an adjective. A host
computes the same bytes before sending and shows the user the room left.
Nothing is ever shortened, and what a scan list shows is the whole name.

### 24.2 Reading and setting

```
GET_NAME   0x47   no argument
  response payload:  u8 name_len, name (UTF-8), u8 adjective_len, adjective (UTF-8)

SET_NAME   0x48   argument u8 name_len, name, u8 adjective_len, adjective
                  a zero length clears that part
  response:        status only. Invalid UTF-8, a control character, a leading
                   or trailing space in either part, or a composed name over
                   29 bytes answers status 1 and changes nothing.
```

The parts are stored before the response is sent. The device advertises
the composed name from the next time it advertises, which is after the
host that set it disconnects. Its device name characteristic, which a host
reads once connected, takes the new name at the next restart; a host that
wants the two to agree at once sends SOFT_RESET after SET_NAME. A factory
reset clears both parts. On a device without capability bit 17 both
opcodes answer status 2.

### 24.3 Twins are numbered by the host

Two devices in one room may compose the same name. The device does not
number itself: which of two is second is known only to a host that hears
them both. A host that lists devices appends a number, starting at 2, to the
second and later devices with the same composed name in that list, in the
order heard, and drops it once the list holds no twin. The number is the
host's alone, never sent to the device and never stored, and every host of
ours renders it the same way.

## Additions to section 13, power-on defaults

| Setting | Default |
|---|---|
| model interval | 0, every window, unless a host's setting was persisted |
| mode | 0, normal; synthetic is never persisted |
| name, adjective | empty, unless a host's setting was persisted |

## Additions to section 15, conformance

Vectors for SET_MODEL_INTERVAL and GET_MODEL_INTERVAL, including a value
below the minimum; GET_MODEL_INFO with the five appended bytes; SET_MODE 3
on a device with and without bit 16; the synthetic packet, type 0x04, with
its malformed forms; an embedding and a prediction carrying input source 3,
for a reader;
model state 3; GET_NAME and SET_NAME for each combination of parts, an
over-length composition, invalid UTF-8, and a leading space; Device Info
vectors claiming bits 15, 16, and 17; and the IntoMind One's profile
updated: it claims all three.

## What this version leaves to the device page, not the contract

The pass time and cadence a device sustains; the generator's statistics and
the measured realism of the synthetic signal; the amplitude the synthetic
signal is scaled to. These are the device's and are documented per device.
