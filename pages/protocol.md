# IntoMind BLE Protocol v1.4

Status: as built in firmware 1.4.2, 2026-10-05. Firmware 1.4.1 built all
of it but section 27, and firmware 1.4.0, 2026-10-02, all but sections 26
and 27. It supersedes 1.3 under the
rules of section 0 of 1.1: a 1.3 host works against a 1.4 device, and a
1.4 host reads a 1.3 device's version and asks it nothing new.

What 1.4 adds:

- **USB power** (section 25): a device that is not run on its wearer while
  plugged in refuses to stream the natural signal while USB power is
  present, and stops a stream of it when USB power appears. The generated
  signal of section 22 still streams. One control status.
- **The heads' encoder ids in a request of their own** (section 26), so
  that every answer fits. One control opcode.
- **Every embedding notification within 156 bytes** (section 27), so that
  every notification but EEG Data fits the smallest MTU the contract
  allows, as section 3 of 1.0 has always said. No new number.

Two things defined earlier change. The LIST_HEADS trailer of 1.3 is
withdrawn, because with it the answer is longer than any answer may be,
and no device ever sent it (section 26.1). And the size of an embedding
notification, which section 19.2 of 1.2 tied to the negotiated MTU with a
wrong count, is now at most 156 bytes on every link (section 27). Nothing
else already defined in 1.0, 1.1, 1.2, or 1.3 changes meaning, size, or
number.

Device Info's `app_slot_bytes` and `weights_image_bytes` keep their
meaning. Firmware 1.4.0 divides its flash anew and reports 290816 and
401408 in them, where the field list of 1.0 shows the earlier
237568 and 507904. A host reads the two fields and never assumes them.

## Numbers assigned by 1.4

| Kind | Number | Meaning |
|---|---|---|
| Control status | 7 | refused while USB power is present, section 25 |
| Control opcode | 0x8A | LIST_HEAD_ENCODERS, section 26 |

None of these collides with a number in use or reserved (section 14 of
1.1, the numbers of 1.2 and 1.3). Control status 6 stays unassigned,
because the Update service answers 6 for a failed verification, and a
reader that sees both services should never meet one number with two
meanings.

## 25. USB power

The IntoMind One is not worn while it is plugged in. From 1.4 the device
holds to that itself: nothing that needs the device on someone's head runs
while USB power is present. USB power is what Status reports as
`usb_present`, flag bit 0.

### 25.1 What is refused

While `usb_present` is set, START_STREAM answers status 7 unless the
device is in the synthetic mode of section 22. That covers every mode that
reads the converter: the natural signal from the electrodes (mode 0), the
converter's own test signal (mode 1), and its shorted inputs (mode 2). The
converter is not started. Electrode contact quality and everything the
device computes from the natural signal ride on such a stream, so they do
not run either.

Settings are not refused: a host may choose a mode, a rate, a gain or a
chain while plugged in, and they take effect on the next stream.

Precedence, extending section 6 of 1.0: invalid argument, then
unsupported, then busy, then USB power, then hardware.

### 25.2 What stops

A stream of the natural signal that is running when USB power appears
ends at once. Its last sample is the last one converted before the device
saw USB power, and no sample after it is streamed. Samples already queued
are still sent, and every packet sent after the device saw USB power
carries `usb_present`, data flag bit 4, so a host can tell from the
packets alone. The next Status message, within one second, reads state 0
with `usb_present` set, and that pair is the reason. A host tells its user
to unplug to record. The samples streamed are complete and the stream
simply ends, so there is no gap inside it to mark. The device does not
resume when USB power goes away. A host starts a new stream.

### 25.3 What runs

The synthetic signal of section 22 streams while plugged in, with its
processing chain and the one model of section 22. So does everything that
does not read the electrodes: the connection, Device Info, settings, the
name, the lamp, updates, battery and charger state.

### 25.4 A 1.3 host

A 1.3 host does not know status 7. Under section 0 of 1.1 it treats any
status other than 0 as a refusal, so its user sees a stream that did not
start, or one that ended, with `usb_present` set in the same Status.

## 26. The heads' encoder ids

### 26.1 LIST_HEADS answers as it did in 1.2

1.3 appended to LIST_HEADS the encoder id each head names, one eight byte
id per record after the records (section 21.1 of 1.3). An IntoMind One
lists five records, the built-in slot and its four user slots, and with
the trailer that answer is 194 bytes. No answer on Control Response may be
longer than 156 bytes (section 3 of 1.0), so no device ever sent it:
firmware 1.3 and 1.4.0 answered LIST_HEADS with status 2.

From 1.4 LIST_HEADS answers exactly as in 1.2: `u8 active_slot, u8
n_entries`, then the records, and nothing after them. On the IntoMind One
the answer is 154 bytes. A 1.2 or 1.3 host parses it as it always has. The
encoder ids are in LIST_HEAD_ENCODERS.

### 26.2 LIST_HEAD_ENCODERS

| Opcode | Name | Arg | Response payload | Notes |
|---|---|---|---|---|
| 0x8A | LIST_HEAD_ENCODERS | | `u8 n_entries`, then `n_entries` records of 9 bytes | one record for each LIST_HEADS record, in the same order |

```
u8     slot
u8[8]  encoder_id   the id the head names, all zero for an empty slot or a head that does not say
```

On the IntoMind One the answer is 48 bytes. Without a model runtime the
request answers status 2, as LIST_HEADS does. A device before 1.4 answers
it with status 1, so a host asks it only of a device that reports 1.4 or
later.

A host does with these ids what section 21.1 of 1.3 says. A host that is
refused this request knows nothing of which encoder the heads name, and
shows each head as it shows one that does not say.

### 26.3 Every answer fits

No answer on Control Response, at its largest, is longer than 156 bytes.
A device that fails to compose an answer, which a device that keeps to
this contract never does, answers status 5. It never answers status 2,
which says the device does not do what was asked, and never answers
status 0 with less than the whole answer. The same holds on Update
Control, where the status is 5 as well.

## 27. Embedding notifications fit 156 bytes

Section 3 of 1.0 holds every notification and indication but EEG Data to
156 bytes, so that an MTU of 159, the smallest the contract allows for
them, carries each one whole. Section 19.2 of 1.2 said instead that an
embedding notification carries as many values as fit the negotiated MTU,
and that 96 values fit at that smallest MTU. The count is wrong: after the
28 byte header, 64 values fit. And firmware 1.2 to 1.4.1 kept neither
rule. It filled a part with up to 108 values, 244 bytes, whatever the MTU,
so the launch model's 76 value vectors each went as one notification of
180 bytes, which a host below an MTU of 183 received cut short.

From 1.4, as built in firmware 1.4.2, an embedding notification carries at
most 64 values, 156 bytes, on every link. A vector wider than that goes in
parts exactly as section 19.2 of 1.2 defines: each part names its `first`
value, and every part but the last sets `more_parts`. The launch model's
vectors go in two parts, 64 values and 12. A host puts parts back together
as it always has, so a 1.2 or 1.3 host reads them unchanged, and a
notification from an earlier firmware reads as it did.

No number is assigned, and nothing else changes.
