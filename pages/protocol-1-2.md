# IntoMind BLE Protocol v1.2

Status: in force from firmware 1.2.0, 2026-09-25. It supersedes 1.1 by addition only, under the rules of
section 0 of that document: a 1.1 host works against a 1.2 device, and a
1.2 host reads a 1.1 device's version and asks it nothing new.

What 1.2 adds:

- **The indicator** (section 17): the status lamp's language has three
  levels of verbosity, the host reads and sets the level, the level is kept
  across power cycles, and a host can ask the device to identify itself.
  Capability bit 13.
- **Converter registers, read only** (section 18): the raw configuration
  bytes of the analog converter, for debugging. No write exists. Capability
  bit 14.
- **Embeddings** (section 19): the encoder's output for each window,
  streamed to the host in two forms, the window embedding that heads
  consume and the token sequence that reconstruction consumes, so heads can
  be trained and signal generated without the model's weights ever leaving
  the device. One new characteristic, one new packet type, one byte
  appended to GET_MODEL_INFO. Capability bit 12.
- Three control opcodes for the indicator, one for the registers, one for
  embeddings; two rows in the power-on defaults; conformance vectors for
  every new message.

Nothing already defined in 1.0 or 1.1 changes meaning, size, or number.

## Numbers assigned by 1.2

| Kind | Number | Meaning |
|---|---|---|
| Capability bit | 12 | embeddings, section 19 |
| Capability bit | 13 | indicator, section 17 |
| Capability bit | 14 | converter registers, section 18 |
| Control opcode | 0x34 | GET_CONVERTER_REGISTERS |
| Control opcode | 0x44 | GET_INDICATOR |
| Control opcode | 0x45 | SET_INDICATOR |
| Control opcode | 0x46 | IDENTIFY |
| Control opcode | 0x87 | SET_EMBEDDINGS |
| Characteristic fill | 0x000B | Embeddings (notify) |
| Packet type | 0x03 | embedding |
| GET_MODEL_INFO byte 16 | appended | tokens per channel per window, section 19 |

None of these collides with a number in use or reserved (section 14 of
1.1).

## 17. Indicator

A device that sets capability bit 13 has a status lamp whose language a
host can read and set. The language is one language at three levels of
verbosity. A blink means the same thing at every level that shows it; a
level only decides which things are shown.

### 17.1 Levels

| Level | Value | What the lamp shows |
|---|---|---|
| silent | 0 | nothing, ever |
| reserved | 1 | low battery, and a converter fault at power on. The default. |
| verbose | 2 | everything in reserved, plus waiting for a host, connected, streaming, and update in progress |

The level is kept across power cycles. A factory reset returns it to
reserved. Identify (17.4) is honored at every level, silent included,
because the host asked for it at that moment.

### 17.2 What each thing means

| Shown at | Thing | The device's rule |
|---|---|---|
| reserved, verbose | low battery | the device's own charge estimate, the percent it reports in GET_BATTERY and in Status, has fallen below 20 percent. It clears once the estimate is back above 25 percent, or while the device is on external power. The band keeps the lamp from flickering at the edge. |
| reserved, verbose | converter fault | the analog converter failed the device's check at power on. Nothing can be recorded. |
| verbose | waiting for a host | advertising, not connected |
| verbose | connected | a host is connected, nothing streaming |
| verbose | streaming | samples are leaving the device |
| verbose | update in progress | an image is being carried over the update service |

When more than one thing is true, the lamp shows the most important:
converter fault, then low battery, then update in progress, then streaming,
then connected, then waiting. So in verbose a connected device with a low
battery shows low battery, not connected.

The blink patterns themselves are the device's, documented on its device
page, not in this contract; a host never decodes the lamp. What the
contract fixes is the set of things, their meaning, the levels, and the
priority, so that a host can explain the lamp to a user in words.

### 17.3 Reading and setting the level

```
GET_INDICATOR   0x44   no argument
  response payload:  u8  level        0 silent, 1 reserved, 2 verbose

SET_INDICATOR   0x45   argument u8 level
  response:          status only. A value other than 0, 1, 2 answers status 1.
```

The new level takes effect at once and is stored before the response is
sent.

### 17.4 Identify

```
IDENTIFY        0x46   argument u8 seconds, 1 to 30; 0 stops an identify in progress
  response:          status only. A value above 30 answers status 1.
```

For the asked seconds the lamp shows the device's identify pattern, distinct
from everything in 17.2, whatever the level; then the level's own language
resumes. For a room with several devices.

On a device without capability bit 13 the three opcodes answer status 2.

## 18. Converter registers, read only

A device that sets capability bit 14 lets a host read the raw configuration
registers of its analog converter, for debugging. The values are the chip's
own, as its datasheet defines them; nothing in them is secret, and the
protocol already reports the settings they encode. The contract carries the
bytes and says which family of chip they belong to; what the bytes mean is
the family's datasheet, and a host library may carry that knowledge keyed
on the family the device declares, never on a device name.

```
GET_CONVERTER_REGISTERS   0x34   no argument
  response payload:
  u8      family        1 = the Texas Instruments ADS1299 family (ADS1299, ADS1299-4, ADS1299-6). The IntoMind One carries the ADS1299-4. No other value is defined by 1.2.
  u8      first         address of the first register carried, 0
  u8      count         registers carried
  u8[n]   values        count bytes, consecutive addresses from first, as the chip returned them
```

- **Read only.** No register write exists in this contract and none will be
  added: a write could drive lead-off or bias current into the wearer or
  break the acquisition.
- The device reads the chip when asked. If the chip cannot be read in its
  current state, for example while it is converting continuously, the
  device either pauses the chip for the read without losing samples or
  answers status 3, and says which in its device page. The IntoMind One
  answers status 3 while streaming. It never answers from a copy of what
  it last wrote.
- The ADS1299 family carries 24 registers, addresses 0x00 to 0x17; the
  first is the chip's identity register, which names the exact part and its
  channel count. The host libraries put all 24 into words, from the
  datasheet (SBAS499C).

On a device without capability bit 14 the opcode answers status 2.

## 19. Embeddings

A device that sets capability bit 12 runs its encoder on each window and
sends the result to the host, in one of two forms:

- **The window embedding**: `model_embed_dim` numbers describing the whole
  window, the mean of the tokens below over the live channels and over
  time. It is the same vector a head consumes (section 11), so a head
  trained on these runs on the device unchanged. One notification per
  window.
- **The tokens**: the encoder's output before that pooling, one vector of
  `model_embed_dim` numbers per token, `tokens_per_channel` tokens per live
  channel per window, each token describing its own slice of the window (a
  fifth of a second on the launch model). Reconstruction, and so
  generation, needs these: a token's embedding turns back into the slice
  it came from, the window embedding does not. About eighty tokens per
  window on the launch model with four live channels, some sixty
  notifications.

The weights never leave the device; both forms are outputs of the model,
not the model, and the weights cannot be recovered from them.

`GET_MODEL_INFO` gains one byte, appended at offset 16: `tokens_per_channel`,
the tokens the loaded model produces per channel per window. A 1.1 host
never reads it; a 1.2 host reading a 1.1 device sees the message end at 16
bytes and knows the device sends no tokens.

### 19.1 Enabling

```
SET_EMBEDDINGS   0x87   argument u8 form
                        0 off, 1 the window embedding, 2 the tokens, 3 both
  response:           status only. A value above 3 answers status 1.
```

Embeddings flow only while streaming, with a ready model, and with a form
enabled. **No head is required**: a device with no head, or with
predictions off, still sends them when asked. On a device without
capability bit 12 the opcode answers status 2.

### 19.2 The Embeddings characteristic (notify), fill 0x000B

One vector per notification, or per group of notifications when a vector
does not fit one. A window embedding is one vector; a window's tokens are
one vector per token.

```
offset type    field
0      u8      packet_type        0x03 = embedding
1      u8      flags              bit0 gap_in_window
                                  bit1 duty_reduced (the device skipped windows to stay within its compute budget)
                                  bit2 leadoff_in_window
                                  bit3 more_parts (another notification carries the rest of this window's values)
2      u8      embed_dim          values in the whole embedding
3      u8      first              index of the first value carried in this notification
4      u32     sample_index       raw stream index of the window's first sample
8      u64     device_time        device time of that sample
16     u16     window_samples     window length in raw samples at the current rate
18     u8[8]   encoder_id         the encoder that produced the embedding, as GET_MODEL_INFO reports it
26     u8      input_source       what the window was taken from, as in the prediction header: 0 the stream, 1 the natural signal, 2 the model's own chain
27     u8      token              0xFF for the window embedding; otherwise the token's index, channel-major over all channels: channel × tokens_per_channel + slice. A dead channel's tokens are sent too; the lead-off flag and the stream say which channels were live
28     i16[k]  values             little-endian, each the encoder's output times 4096, saturated, rounded half away from zero: exactly what a head receives (section 11)
```

- A notification carries as many values as fit the negotiated MTU after
  the 28-byte header. With the smallest MTU this contract allows, 96
  values fit in one notification; a vector of up to 128 values takes two.
  Corrected by section 27 of 1.4: 64 values fit at that MTU, and
  from 1.4 a notification carries at most 64 values, 156 bytes, on every
  link.
  Parts of one vector share `sample_index`, `device_time` and `token`; a
  host reassembles by `first` and knows the vector is complete when a part
  arrives without `more_parts`. A window's tokens all carry the window's
  `sample_index`; the window is complete when every token index from 0 to
  channels × `tokens_per_channel` − 1 has arrived.
- Cost, for the launch model at four live channels: the window embedding is
  one notification of 220 bytes per window; the tokens are about eighty
  notifications, some seventeen kilobytes per window, sent at the model's
  cadence. A host that only trains heads asks for form 1.
- The window, its input, and its cadence are the model's (sections 10 and
  16.4): the same window feeds the embedding and, when a head is selected
  and predictions are on, the prediction. Both then carry the same
  `sample_index`. Cadence stays the device's choice within its compute
  budget; windows are self describing.
- `encoder_id` lets a host keep embeddings from different encoders apart.
  A head trained on one encoder's embeddings is only valid on that encoder,
  and section 11 already refuses a head whose encoder does not match.
- A recording that stores embeddings stores `encoder_id`, `input_source`,
  and the chain in force with them, as it does for predictions.

### 19.3 What this makes possible on a host, and what stays off the device

With the window embedding a host trains heads without the weights: fitting
the small open layer of section 11 on recorded embeddings. With the tokens
a host generates signal without the weights: the open reconstruction head
turns each token back into its slice, and synthesis in the embedding space
(mixing, moving, or sampling tokens) followed by reconstruction is
generating synthetic brain data. Both heads and the reconstruction head
stay open and user-changeable; only the encoder is closed.

Generation on the device itself is not offered by 1.2 and cannot be on the
IntoMind One as laid out: the reconstruction head is 38 kilobytes, the
device's one megabyte of flash is fully assigned (two application slots,
each 229 of 232 kilobytes used; the weights, 503,328 of 507,904 bytes used;
four head slots of 4 kilobytes; the bootloader and its state), so nothing
free is as large as 38 kilobytes, and a generated window is 24 kilobytes of samples to carry
over the air where the tokens it would be made from are 17. If a later
device or a smaller model makes it possible, it gets its own packet type,
so a generated sample can never be mistaken for a measured one.

## Additions to section 13, power-on defaults

| Setting | Default |
|---|---|
| indicator level | reserved, unless a host's setting was persisted |
| embeddings | off |

## Additions to section 15, conformance

Vectors for GET_INDICATOR, SET_INDICATOR, IDENTIFY, GET_CONVERTER_REGISTERS,
SET_EMBEDDINGS, and the embedding packet, including a two-part embedding,
each with its malformed forms; Device Info vectors claiming bits 12, 13 and
14; and the IntoMind One's profile updated: it claims all three.

## What this version leaves to the device page, not the contract

The blink patterns and the identify pattern; the converter family's register
map; the exact windows per second a device sustains. These are documented
per device, because they are the device's, and the contract only carries
what a host must be able to rely on across devices.
