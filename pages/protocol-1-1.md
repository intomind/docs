# IntoMind BLE Protocol v1.1

Status: in force from firmware 1.1.0, written 2026-09-25. This document is
the contract between an IntoMind device and any host. Firmware, the api, the
sdk, and the Command Center all implement it. Its canonical home moves to
the api repository at publication. It supersedes 1.0 by addition only: a 1.0
host works against a 1.1 device, and a 1.1 host reads a 1.0 device's version
and asks it nothing new.

What 1.1 adds: the processing chain the device runs on its signal and the
operations to read and set it (section 16); where the model's input comes
from; the bias drive, on devices that claim one; two capability bits; and
two bytes that were reserved, in GET_MODEL_INFO and in the prediction
header.

## 0. Versioning and compatibility

- The device reports `proto_major.proto_minor` in Device Info. This document
  is 1.1.
- Within major version 1, a minor version only adds: new opcodes, new
  characteristics, new capability bits, new fields appended to Device Info.
  Nothing already defined changes meaning, size, or number. A 1.0 host works
  against every 1.x device by ignoring what it does not know.
- A major version change is allowed to break the wire format. The device
  advertises the major version so a host can refuse or adapt.
- Numbers that were used by any earlier firmware are never reused for a
  different meaning. Section 14 lists them.
- The wire formats of Device Info (first 27 bytes), EEG Data, the Control
  Point, and Status are byte for byte the v0.1 formats.

## 1. Design invariants

1. **On-device time is authoritative.** Every sample carries a device time
   captured on the device, in hardware, at the converter's data-ready edge.
   The host maps device time onto its own clock. It never derives sample
   times from packet arrival.
2. **The timeline is never silently corrupted.** A monotonic `sample_index`
   is the source of truth for continuity. Any loss is announced with an
   explicit discontinuity flag and count. The host reconstructs a timeline
   with marked holes, never a silent splice.
3. **The device processes its signal, and the stream declares what
   produced it.** Filters are one class of the preprocessing a device
   hosts. When a chain is in force only its output streams, written back
   into the converter's own count domain so the scaling rule below is
   unchanged; when the chain is empty the natural signal streams. The chain
   is readable at any time, cannot change while streaming, and is what a
   recording stores beside its samples. There is no raw-versus-processed
   flag anywhere: a flag says nothing about what a signal is. The on-device
   model of section 10 consumes its own copy, taken from the stream unless
   a host points it elsewhere, and is additive: turning it on or off
   changes nothing about the stream.
4. **The link is private.** Data, control, status, and updates require an
   encrypted, bonded connection. Neural data belongs to its owner.
5. **The contract adapts to hardware.** Capabilities and capacities are
   read from the device, so one contract serves devices with different
   channel counts, battery sensing, model presence, or slot sizes.
6. **The model can never hurt the instrument.** Every model surface is
   optional. A device with no valid model behaves exactly like a device with
   no model at all, and acquisition never waits on inference.

## 2. GATT structure

One primary service. 128-bit UUIDs from the base
`f3a1xxxx-2c4b-4d1e-9a6f-1b2c3d4e5f60`, where `xxxx` is the fill below.

| Fill | Characteristic | Properties | Purpose |
|---|---|---|---|
| `0001` | Service | | IntoMind Neural Stream |
| `0002` | Device Info | Read | identity, capabilities, capacities (section 4) |
| `0003` | Control Point | Write, Write Without Response | commands (section 6) |
| `0004` | Control Response | Indicate | command results |
| `0005` | EEG Data | Notify | sample packets (section 5) |
| `0006` | Status | Read, Notify | live device status (section 7) |
| `0007` | reserved | | held by an earlier development firmware, never reused |
| `0008` | Update Control | Write, Indicate | update and head transfer commands (section 9) |
| `0009` | Update Data | Write Without Response | transfer payload bytes (section 9) |
| `000A` | Predictions | Notify | model outputs (section 10) |

All characteristics except Device Info require an encrypted, bonded link
(section 12). Every characteristic value is at most 244 bytes, so nothing
requires ATT fragmentation at an ATT MTU of 247. Notifications and
indications are sized to the negotiated MTU, see section 3.

## 3. Advertising and connection

- Advertising data: flags, complete list of 128-bit service UUIDs holding
  the service UUID.
- Scan response: complete local name `IntoMind-1-XXXX`, where `XXXX` is the
  last two bytes of `device_id` in uppercase hex. Multiple units are
  distinguishable before connecting.
- Hosts filter on the service UUID or on the name prefix `IntoMind-`.
- The device requests an ATT MTU of 247 and a connection interval that
  sustains the stream (7.5 to 15 ms while streaming). Hosts should accept
  the largest MTU they can. The device sizes EEG Data packets to the
  negotiated MTU, so streaming works at any MTU of 44 or more (one sample
  per packet at four channels). Other notifications and indications are at
  most 156 bytes and require an MTU of at least 159. Every current phone,
  desktop, and browser stack negotiates more than this.
- Bonding uses LE Secure Connections with Just Works (the device has no
  display or keypad). The device stores up to four bonds and evicts the
  least recently used when a fifth host pairs.

## 4. Device Info (read)

Little-endian. Read once per connection. Re-read after a weights update
activates (section 9), since model fields can change then.

```
offset type    field
0      u8      proto_major            1
1      u8      proto_minor            0
2      u8      fw_major
3      u8      fw_minor
4      u8      fw_patch
5      u8      channel_count          4 on the IntoMind One
6      u8      adc_bits               24
7      u32     time_tick_hz           device time ticks per second, 1000000
11     u32     vref_uv                converter reference in microvolts, 4500000
15     u16     capabilities           bitmask, table below
17     u8      supported_rates        bit0 250, bit1 500, bit2 1000 SPS
18     u8      reserved
19     u8[8]   device_id              stable per-unit id from the SoC factory id
--- end of the v0.1 layout, 27 bytes ---
27     u8      info_len               total length of Device Info in bytes, 76 in 1.0
28     u8      hw_major               hardware revision, 1
29     u8      hw_minor               1
30     u8      hw_patch               5
31     u8      reserved
32     u8[8]   fw_build_id            identifies the exact firmware image
40     u16     model_embed_dim        embedding width, 96 on the IntoMind One, 0 = no model runtime
42     u16     model_native_sps       the model's native rate, 500
44     u16     model_window_samples   samples per prediction window at the native rate, 2000
46     u8      head_slots             user head slots, 4
47     u8      head_max_outputs       largest out_dim a head may have, 32
48     u16     head_slot_bytes        capacity of one head slot, 4096
50     u16     update_chunk_max       largest Update Data write accepted, 244
52     u32     app_slot_bytes         application image capacity including its header, 237568
56     u32     weights_image_bytes    weights image capacity including its header, 507904
60     u8[16]  reserved               zero
76     end
```

A host reads `info_len` and never reads past it. A later 1.x device may
report a larger `info_len` with fields appended after offset 76.

Read Device Info again after any update activates, since the firmware
version, the build id, and every model field can change across one.

Capabilities:

| Bit | Name | Meaning |
|---|---|---|
| 0 | battery_voltage | `Status.battery_percent` and GET_BATTERY carry measured values |
| 1 | battery_low_flag | the hardware has a low battery indicator |
| 2 | leadoff | lead-off detection available |
| 3 | test_signal | internal test signal mode available |
| 4 | dcdc_mode | reserved for converter power mode selection |
| 5 | input_short | input short mode available |
| 6 | update | the Update service is present and accepts application and weights images |
| 7 | model | a model runtime is present in this firmware |
| 8 | model_ready | valid weights were loaded at the time of this read, predictions can be enabled |
| 9 | heads | user head slots are present, head operations are accepted |
| 10 | pipeline | the device runs a processing chain and answers the operations of section 16. The IntoMind One sets this bit |
| 11 | bias_drive | the device has a bias drive a host may set and read (section 16). The IntoMind One does not set this bit: its bias output reaches a pad and no further |
| 12 to 15 | reserved | zero |

A device without a battery sense circuit reports bit 0 clear and
`battery_percent` = 0xFF. The IntoMind One reports bit 0 set.

## 5. EEG Data (notify)

Header little-endian. The sample payload is the converter's own byte order:
big-endian two's complement 24-bit integers, most significant byte first.
The device copies converter bytes without per-sample swapping. The host
sign-extends and scales.

```
offset type   field
0      u8     packet_type            0x01 = EEG data
1      u8     flags                  bit0 discontinuity_before_this_packet
                                     bit1 leadoff_active
                                     bits2-3 mode (0 normal, 1 test, 2 short)
                                     bit4 usb_present
2      u16    samples_lost_before    convenience count, saturates at 0xFFFF
4      u32    sample_index           index of the first sample, monotonic, wraps at 2^32
8      u64    device_time            device time of the first sample's data-ready edge, in time_tick_hz ticks
16     u8     n_samples
17     u8     loff_statp             lead-off status latched with the last sample in this packet, bit n = channel n+1
18     u8     gain_code              0..6 = gain 1, 2, 4, 6, 8, 12, 24
19     u8     rate_code              4 = 1000, 5 = 500, 6 = 250 SPS
20     ...    payload                n_samples x channel_count x 3 bytes
```

- `n_samples` is at most the value set by SET_SAMPLES_PER_PACKET and never
  more than fits the negotiated MTU. One notification is one packet.
- Scaling on the host: `microvolts = raw × (2 × vref_uv) / (gain × 2^24)`.
  At gain 24 and a 4.5 V reference one count is about 0.02235 µV.
- Continuity on the host: the expected next `sample_index` is the previous
  packet's `sample_index` plus its `n_samples`. Compute
  `step = new_index − expected` as a signed 32-bit difference so the
  index's own wrap is exact.
  - `step == 0` and bit0 clear: continuous.
  - `step > 0`: `step` samples were lost. They span the corresponding
    device time range. `samples_lost_before` carries the same number when
    it fits in 16 bits.
  - `step <= 0`, or bit0 set with `step == 0`: the timeline re-based
    (RESET_EPOCH or a stream start). This is a break, not a loss. The
    device sets bit0 and `samples_lost_before` = 0. A host must never turn
    a non-positive step into a loss count. Taking the unsigned difference
    here reports a loss that never happened.
- Every sample in an epoch is acquired under one configuration, because
  configuration changes are refused while streaming.

## 6. Control Point (write) and Control Response (indicate)

A request is `[opcode, arg?]`, one or two bytes. Exactly the opcodes marked
with an argument take one, and they require it. Any other length is invalid.
Two opcodes new in 1.1, SET_PIPELINE and SET_PREDICTION_INPUT, carry a
payload after the opcode byte whose layout section 16 defines; a request on
one of them is as long as its payload. The device answers on Control
Response with `[opcode, status, payload?]`.

Status codes:

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | invalid argument, or malformed request |
| 2 | unsupported by this device or build |
| 3 | busy: refused while streaming or while a transfer is active |
| 4 | not streaming |
| 5 | hardware error |

Precedence when several apply: invalid argument, then unsupported, then busy,
then hardware. A request is validated before device state is consulted.

Opcodes carried over from v0.1, unchanged:

| Opcode | Command | Arg | Notes |
|---|---|---|---|
| 0x01 | START_STREAM | | begins continuous conversion and streaming |
| 0x02 | STOP_STREAM | | |
| 0x10 | SET_RATE | rate_code | refused with 3 while streaming |
| 0x11 | SET_GAIN | gain_code | refused with 3 while streaming |
| 0x20 | SET_MODE | 0, 1, 2 | normal, test signal, input short. Refused with 3 while streaming |
| 0x30 | SET_LEADOFF | 0, 1 | refused with 3 while streaming |
| 0x40 | TIME_SYNC | | payload `u64 device_time` captured at request receipt |
| 0x41 | SET_SAMPLES_PER_PACKET | 1..N | N is the largest count that fits the MTU. Larger values are clamped to N and reported in the payload as `u8 applied` |
| 0x50 | RESET_EPOCH | | zero `sample_index`, start a fresh epoch. The next packet carries the discontinuity flag with a zero loss count |
| 0xF0 | SOFT_RESET | | re-initialize the device. The link drops |

Opcodes new in 1.0:

| Opcode | Command | Arg | Payload | Notes |
|---|---|---|---|---|
| 0x42 | GET_BATTERY | | `u16 battery_mv, u8 battery_percent, u8 charger_state` | requires capability bit 0, else status 2. `battery_percent` follows Status |
| 0x43 | GET_BOOT_INFO | | `u8 active_slot, u8 boot_reason, u8 slot_state, u8 reserved, u32 boot_count` | table below |
| 0x53 | CLEAR_BONDS | | | forget every bond except the requesting host's. Takes effect at the next disconnect |
| 0x80 | SET_PREDICTIONS | 0, 1 | | status 2 without a ready model or a selected head. Predictions flow only while streaming |
| 0x81 | SELECT_HEAD | slot | | 0 = the built-in head, 1..head_slots = user slots. Status 1 for an empty or unknown slot |
| 0x82 | LIST_HEADS | | see below | |
| 0x83 | REMOVE_HEAD | slot | | 1..head_slots only. Refused with 3 while streaming |
| 0x84 | GET_MODEL_INFO | | see below | |

GET_BOOT_INFO fields: `active_slot` 0 = A, 1 = B. `slot_state` 0 = trial (the
running image has not yet confirmed itself), 1 = confirmed. `boot_count`
counts boots of this unit since manufacture. `boot_reason`:

| Value | Reason |
|---|---|
| 0 | power on |
| 1 | reset pin |
| 2 | software reset |
| 3 | watchdog |
| 4 | CPU lockup or system fault |
| 5 | update activation |
| 6 | rollback, the bootloader reverted to the previous image |
| 0xFF | unknown |

A watchdog or fault reset is also visible in the stream as a discontinuity.

LIST_HEADS payload: `u8 active_slot, u8 n_entries`, then `n_entries` records
of 30 bytes:

```
u8     slot        0 = built-in
u8     state       0 empty, 1 valid, 2 invalid (failed its hash at load)
u16    out_dim
u8[8]  head_id     first 8 bytes of the head's SHA-256, zero when empty
u8[16] name        UTF-8, zero padded
u8[2]  reserved
```

`n_entries` is `1 + head_slots` when a model runtime is present. Without one
the request answers status 2.

GET_MODEL_INFO payload:

```
u8     model_state      0 no runtime, 1 runtime present but no valid weights, 2 ready
u8     active_head      slot, or 0xFF when none
u8     predictions_on   0, 1
u8     reserved
u8[8]  encoder_id       identity of the loaded weights, zero unless ready
u8     weights_major
u8     weights_minor
u8     weights_patch
u8     input_classes    1.1: the signal classes the loaded model takes, bit 0 time domain, bit 1 representation. A 1.0 device sends 0, which reads as the time domain
```

Opcodes new in 1.1. A 1.0 device answers status 1 to them, which a host
never sees because it sends them only to a device whose Device Info sets
the capability bit named for each.

| Opcode | Command | Arg or payload | Payload | Needs | Notes |
|---|---|---|---|---|---|
| 0x90 | GET_PIPELINE_CATALOG | | catalog, section 16 | pipeline | the stage kinds this device runs |
| 0x91 | GET_PIPELINE | | `u8 origin`, chain | pipeline | origin 0 = the device's default for the current rate, 1 = set by a host |
| 0x92 | SET_PIPELINE | chain | | pipeline | refused with 3 while streaming, with 1 when a stage cannot run at the current rate; the chain in force is then untouched |
| 0x93 | CLEAR_PIPELINE | | | pipeline | the natural signal, a host's choice. Refused with 3 while streaming |
| 0x94 | RESTORE_PIPELINE_DEFAULT | | | pipeline | the device's default for the current rate. Refused with 3 while streaming |
| 0x85 | SET_PREDICTION_INPUT | `u8 source`, chain | | model | 0 = the stream, 1 = the natural signal, 2 = a chain of the model's own, which only source 2 carries. Status 1 when the chain cannot run at the current rate or produces a class the model does not take; status 2 without a model runtime. Allowed while streaming |
| 0x86 | GET_PREDICTION_INPUT | | `u8 source`, chain | model | the chain in effect for the model: the stream's for source 0, empty for 1, its own for 2 |
| 0x32 | SET_BIAS | 0, 1, 2 | | bias_drive | off, on, loop open. Refused with 3 while streaming |
| 0x33 | GET_BIAS_DIAGNOSTIC | | `i16 mean_mv, i16 sd_mv, i16 min_mv, i16 max_mv` | bias_drive | the bias output over the device's own window |

SET_RATE, unchanged in form, now also carries the chain: the device's own
default is recomposed for the new rate, and a host's chain that cannot run
at the new rate refuses the rate with status 1, so the host changes the
chain first. Nothing is ever trimmed in silence.

Opcodes 0x60 to 0x6F are reserved for factory and bench builds. Production
firmware answers status 2 to them.

## 7. Status (read and notify)

```
u8   state                 0 idle, 1 streaming
u8   mode
u8   gain_code
u8   rate_code
u8   charger_state         0 no input, 1 charging, 2 complete, 3 fault, 4 standby
u8   battery_percent       0..100, or 0xFF unknown
u8   loff_statp            as latched with the most recent sample acquired
u8   flags                 bit0 usb_present, bit1 buffer_high_watermark
u16  dropped_total         samples acquired but never delivered this power-on, saturates
u16  buffer_fill           samples currently buffered on the device
```

Notified on any state change and at about 1 Hz while connected.

- `battery_percent` is a state of charge estimate from the measured pack
  voltage on the IntoMind One. GET_BATTERY carries the voltage itself.
- `loff_statp` mirrors the per-packet value. Before the first sample of a
  session it reads 0. Use the per-packet copy for contact tracking.
- `buffer_high_watermark` is set while `buffer_fill` is at or above three
  quarters of the device's buffer. Read it as backpressure.
- `dropped_total` counts every sample acquired but never delivered: buffer
  overflow, conversions the acquisition path could not read in time, and
  anything discarded at an epoch boundary. Only a reboot clears it. It is
  telemetry. The authoritative account of what a host missed is
  `sample_index` continuity.

## 8. Time sync (informative)

Device time is monotonic and free running. The converter's clock and the
host's clock drift relative to each other by tens of parts per million, so
a host that needs alignment better than about 10 ms re-syncs every few
minutes:

1. Note host time `T1`, write TIME_SYNC.
2. The device captures `Td` at receipt and returns it.
3. Note host time `T2` at the response. Estimate `offset ≈ (T1+T2)/2 − Td`
   with uncertainty `±(T2−T1)/2`. Regress `offset` over several syncs to
   estimate skew.
4. Map any sample: `host_time ≈ device_time × (1 + skew) + offset`.

Multiple devices each sync independently to the same host clock, which puts
them on one timebase at millisecond alignment without wires.

## 9. Update service

The Update service carries three kinds of transfer: an application image,
a weights image, and a user head. Application and weights images are
produced by IntoMind, signed, and encrypted. A host carries them as opaque
bytes and needs no key. Heads are plain blobs in the format of section 11,
made by anyone.

### 9.1 Rules

- A transfer is refused with status 3 while streaming. Stop the stream
  first.
- One transfer at a time. START while one is in progress is refused with
  status 3. ABORT ends it.
- The running application is never written. An application image goes to
  the idle slot. The device tells the host which slot that is, and the
  host sends the image variant built for that slot.
- A weights image is written in place. If power fails during the write the
  partition fails verification at the next boot, predictions are
  unavailable, and everything else works. A new weights transfer repairs
  it.
- A head is written to the slot named in START. Slot 0, the built-in head,
  cannot be written or removed.
- The device keeps a transfer's progress in memory across a disconnect.
  START with identical parameters resumes at the reported offset. A reboot
  starts over.

### 9.2 Update Control (write, indicate)

Request `[op, ...]`, response `[op, status, payload?]`.

Status codes:

| Code | Meaning |
|---|---|
| 0 | OK |
| 1 | invalid argument or malformed request |
| 2 | unsupported (no such target on this device) |
| 3 | busy: streaming, or a transfer is already active |
| 4 | no transfer in progress |
| 5 | flash error |
| 6 | verification failed, see `verify_result` |

Operations:

| Op | Command | Request | Response payload |
|---|---|---|---|
| 0x01 | START | `u8 target, u8 slot, u32 total_len, u8[8] transfer_id` | `u8 target_slot, u16 chunk_max, u32 resume_offset` |
| 0x02 | QUERY | | `u8 state, u32 offset, u32 crc32` |
| 0x03 | FINISH | | `u8 verify_result` |
| 0x04 | ACTIVATE | | |
| 0x05 | ABORT | | |

- `target`: 1 application, 2 weights, 3 head.
- `slot`: for a head, 1..head_slots. Zero otherwise.
- `total_len`: the exact number of bytes the host will send. For images
  this is the envelope length (section 9.4). For a head it is the blob
  length.
- `transfer_id`: the first 8 bytes of the SHA-256 of the full transfer.
  The device uses it only to recognize a resume.
- `target_slot`: for an application, the slot that will receive the image,
  0 = A or 1 = B. The host must send the variant linked for that slot.
  Zero for other targets.
- `chunk_max`: the largest Update Data write the device accepts. Equal to
  `update_chunk_max` in Device Info unless the MTU is smaller.
- `resume_offset`: bytes already accepted from an identical earlier START.
  The host continues from this offset.
- QUERY `state`: 0 idle, 1 receiving, 2 complete (FINISH verified), 3
  failed. `offset` is the number of bytes accepted so far. `crc32` is the
  IEEE 802.3 CRC-32 (the zlib CRC) over those bytes as sent, so a host
  can check it against its own copy without any key.
- FINISH verifies the whole transfer and answers status 0 with
  `verify_result` 0, or status 6 with the reason. After status 0 the
  transfer state is complete and ACTIVATE is allowed.
- ACTIVATE for an application: the device marks the new image for a trial
  boot, confirms the indication, then resets within one second. The link
  drops. If the new image fails to confirm itself, the bootloader returns
  to the previous image and GET_BOOT_INFO reports reason 6.
- ACTIVATE for weights: the device confirms the indication and then
  resets, the same way. Weights are verified at every boot, so restarting
  is what puts the new ones in force and what proves they are sound
  before anything runs on them. If they are not, the device comes back
  with predictions unavailable and everything else working.
- ACTIVATE for a head: status 2. A head is written and verified by FINISH
  and selected with SELECT_HEAD.

`verify_result`:

| Value | Meaning |
|---|---|
| 0 | verified |
| 1 | length differs from `total_len` |
| 2 | malformed envelope or image header |
| 3 | target mismatch between START and the image |
| 4 | slot mismatch: the image is linked for the other slot |
| 5 | content hash mismatch |
| 6 | signature invalid |
| 7 | image security counter is lower than the installed image's |
| 8 | head dimensions do not match this device |
| 9 | flash write failure |
| 10 | unknown key id |

### 9.3 Update Data (write without response)

Each write appends its bytes to the transfer. No framing, at most
`chunk_max` bytes per write. The link layer delivers writes in order and
without loss. A host paces itself with QUERY, for example every 32 writes,
and compares `offset` and `crc32` with its own count.

### 9.4 Image envelope

An application or weights image travels inside an envelope whose first 32
bytes are plain and describe the payload. The remainder is encrypted and
opaque to the host.

```
offset type    field
0      u8[4]   magic            "IMUP"
4      u8      envelope_version 1
5      u8      target           1 application, 2 weights
6      u8      slot_link        application: 0 = built for slot A, 1 = built for slot B. 0xFF for weights
7      u8      key_id
8      u8[16]  nonce
24     u32     plain_len        length of the encrypted payload in bytes
28     u8[4]   reserved
32     ...     payload          plain_len bytes
```

A release of the application ships as two envelopes, one per `slot_link`.
The host reads `target_slot` from START and sends the matching one. The
device rejects a mismatch with `verify_result` 4 before any flash is
written.

## 10. Predictions (notify)

Model outputs, one notification per window. Present in the GATT table on
every device with a model runtime. Notifications flow only while streaming,
with predictions enabled, a ready model, and a selected head.

```
offset type    field
0      u8      packet_type        0x02 = prediction
1      u8      flags              bit0 gap_in_window
                                  bit1 duty_reduced (the device skipped windows to stay within its compute budget)
                                  bit2 leadoff_in_window
2      u8      head_slot
3      u8      n_outputs
4      u32     sample_index       raw stream index of the window's first sample
8      u64     device_time        device time of that sample
16     u16     window_samples     window length in raw samples at the current rate
18     u8[8]   head_id
26     u8      input_source       1.1: what the window was taken from, 0 the stream, 1 the natural signal, 2 the model's own chain. A 1.0 device sends 0
27     u8      reserved
28     f32[n]  outputs            n_outputs little-endian IEEE 754 values
```

- The window is the `window_samples` raw samples starting at `sample_index`.
  A host aligns predictions to its recording through the same index it
  uses for the raw stream.
- The model consumes its own copy of the stream resampled to
  `model_native_sps`. At the native rate a window is `model_window_samples`
  raw samples. At 250 SPS it is half that.
- Each output is `scale[o] × (bias[o] + Σ W[o][i] × e[i])` for the selected
  head (section 11). The host applies any activation it wants.
- Cadence is the device's choice within its compute budget. Windows are
  self describing, so a host never assumes a fixed hop.
- `head_id` names the head that produced the outputs. Recordings should
  store it with the predictions.

## 11. Heads

A head is weights, never code. It maps the model's embedding to a small
number of outputs.

The embedding `e` is a vector of `model_embed_dim` signed 16-bit integers
in units of 1/4096. The runtime computes the embedding in floating point
and quantizes it at that fixed scale before running a head. The scale is
part of this contract: changing it would change every head ever trained.
The sdk runs the same runtime on the host and produces the same integers,
which is what lets a head trained on a host behave identically on the
device.

Head blob, little-endian:

```
offset type            field
0      u8[4]           magic            "IMHD"
4      u8              format_version   1
5      u8              kind             1 = linear
6      u16             in_dim           must equal model_embed_dim
8      u16             out_dim          1..head_max_outputs
10     u8[16]          name             UTF-8, zero padded
26     u8[6]           reserved         zero
32     i8[out_dim×in_dim] weights       row major, one row per output
       i32[out_dim]    bias
       f32[out_dim]    scale
       u8[32]          sha256           over every preceding byte
```

- `head_id` is the first 8 bytes of `sha256`.
- On FINISH the device checks magic, version, kind, `in_dim` against its
  embedding width, `out_dim` against `head_max_outputs`, total length
  against the field sizes, and the hash. Any failure is `verify_result` 8
  (dimensions) or 5 (hash) and nothing is stored.
- Slot 0 holds the built-in head that ships with the weights image. User
  slots are 1..head_slots. A head blob for the IntoMind One is at most
  `head_slot_bytes`, which the format satisfies at every allowed size.
- Removing or overwriting the active head deselects it. Predictions stop
  until SELECT_HEAD names another.

## 12. Security

- LE Secure Connections with bonding are required for every characteristic
  except Device Info. Pairing is Just Works. This defeats passive
  eavesdropping, which is the primary threat to neural data. It does not
  defend against an active attacker present during the initial pairing,
  which is the accepted limit of a device with no display or button.
- Update images are signed. The device installs nothing whose signature it
  cannot verify, and a running image never writes over itself. A failed
  new image rolls back automatically.
- Local first. No cloud dependency. Any network feature of a host
  application is opt in and never a precondition for using the device.

## 13. Power-on defaults

| Setting | Default |
|---|---|
| rate | 500 SPS (`rate_code` 5) |
| gain | 24 (`gain_code` 6) |
| mode | normal |
| lead-off | off |
| samples per packet | the largest count that fits the negotiated MTU |
| streaming | off |
| predictions | off |
| active head | slot 0 when a ready model has a built-in head, else none |
| processing chain | the device's default, section 16, unless a host's chain was persisted |
| model input | the stream |
| bias drive | off, on every device |

## 14. Reserved numbers

Never reused for another meaning. Production firmware answers status 2 to
the opcodes.

| Kind | Numbers | Note |
|---|---|---|
| Control opcodes | 0x12, 0x13, 0x31, 0x70, 0x71 | earlier development firmware |
| Control opcodes | 0x60 to 0x6F | factory and bench builds |
| Characteristic fill | 0x0007 | earlier development firmware |
| Packet types | 0x01 EEG data, 0x02 prediction | assigned |

## 15. Conformance

The reference codec for every message in this document is a small library
that both the firmware and the host tooling build unchanged, so an encoder
on one side and a decoder on the other are the same code. Its test vectors
are the conformance suite for any independent implementation. A host
implementation is conformant when it decodes every vector to the documented
fields and refuses every malformed vector.

The vectors are published as one JSON file, emitted by the firmware from
the codec it runs. Every message kind in this document appears there, and
so does a set of malformed messages for each kind, each with the reason it
is refused: truncated, invalid, or reserved.

Two rules govern the file itself, so that a reader in any language gets the
same answer from it.

- **A 64-bit field is written as a decimal string.** A device time runs past
  what a JSON number holds exactly. A reader that parses one as a
  floating-point number lands a few ticks away, and it then agrees with an
  expectation that was rounded the same way, so the mistake passes unseen.
  Parse these as integers.
- **A count that does not exist is written as null, never as zero.** A break
  in the timeline has no extent, and zero there would claim that nothing was
  lost.

## 16. Processing

New in 1.1. A device that sets capability bit 10 runs a processing chain on
its signal and offers these operations.

### 16.1 Chains, stages, and classes

A chain is an ordered list of stages. Each stage names a kind from the
device's catalog and carries up to four sixteen-bit parameters whose units
the kind defines. The empty chain is the natural signal. Every kind belongs
to a class:

| Class | Value | What it does to the signal |
|---|---|---|
| map | 0 | keeps the rate and the kind of signal; map stages layer freely |
| representation change | 1 | replaces the signal with something else, at its own rate |
| detector | 2 | adds annotations and passes the signal on |

This version defines three kinds, all map stages:

| Kind | Value | Parameters, in tenths of a hertz | Rule |
|---|---|---|---|
| high-pass | 1 | `corner` | at least 1 |
| low-pass | 2 | `corner` | 0 means the automatic corner at four tenths of the sample rate |
| notch | 3 | `low_edge, high_edge` | a band, high above low, any band |

A corner or band edge at or above nine tenths of the Nyquist rate is
refused, as is a high-pass at or above the low-pass. The catalog states how
many instances of a kind a chain may hold. Kinds of the other two classes
will be added by later minors; a device lists in its catalog only what it
runs, and refuses a chain that names anything else.

Chain descriptor:

```
u8      n_stages           0 is the natural signal
per stage:
u8      kind
u8      n_params
u16[n]  params             little-endian
```

At most 12 stages, at most 4 parameters per stage. A descriptor that says
more stages or parameters than it carries is truncated; a stage of kind
zero, more than four parameters, more than twelve stages, or bytes after the
last stage is invalid.

Catalog (GET_PIPELINE_CATALOG payload): `u8 n_kinds`, then records of 12
bytes:

```
u8     kind
u8     class
u8     n_params
u8     max_instances
u8[8]  name               ASCII, zero padded
```

### 16.2 What a chain does to the stream

Only the chain's output streams. Each stage runs in the converter's own
count domain and the result is rounded back into twenty-four bits, so the
scaling rule of section 5 applies unchanged, and the timestamp of a
processed sample is the timestamp of the natural sample it corresponds to.
Changing the chain while streaming is refused, so one epoch has one chain;
a host reads GET_PIPELINE at every stream start and stores the answer with
the recording. A stream restart, as ever, is a flagged break.

### 16.3 Defaults and persistence

The chain is on from the first boot. The device's default is a 0.5 Hz
high-pass, the mains bands the rate can represent (both mains fundamentals
and their second and third harmonics, four hertz wide, until a host removes
the ones that do not apply), and the automatic low-pass. The bands are 48
to 52, 58 to 62, 98 to 102, 118 to 122, 148 to 152 and 178 to 182 Hz. At
250 samples a second the last three reach past nine tenths of the Nyquist
rate, 112.5 Hz, so the default there holds three bands. The automatic
low-pass sits at 100, 200 and 400 Hz at 250, 500 and 1000 samples a
second. A notch places its null at the middle of its band and runs as two
sections, so mains 0.03 Hz off its nominal frequency is more than 60 dB
down. The chain in force
persists on the device across power cycles, so every host sees the same
instrument. `origin` in GET_PIPELINE says whether the chain in force is the
device's default, which the device recomposes at every rate change, or a
host's, which binds the rate as section 6 describes.

### 16.4 The model's input

The model follows the stream unless a host points it elsewhere with
SET_PREDICTION_INPUT: at the natural signal, or at a chain of its own, run
beside the stream's on the same natural samples, without touching the
stream. The setting holds until changed or until predictions are turned
off. Every prediction carries its `input_source`. The model declares the
signal classes it takes in `input_classes` of GET_MODEL_INFO, and a chain
for the model is refused when its output class is not among them; nothing
in the contract fixes what a model may consume.

### 16.5 Bias

The bias amplifier is off at power on, on every device. A device that sets
capability bit 11 lets a host set it off, on, or loop open, and read the
bias output's mean, spread, minimum and maximum in millivolts. On a device
without the bit both operations answer status 2.

