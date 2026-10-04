# The device

## What is in the box

- The headset, with four electrodes and a reference.
- A strap.
- A USB-C cable for charging.

## Charging

Plug the USB-C cable into any ordinary charger or a computer. The charge
indicator shows what the charger is doing. Charging from empty takes
about an hour and three quarters.

The device records on its battery only. While it is plugged in it charges
and stays connected, but it does not record from the electrodes: a
recording started on the cable is refused, and one that is running stops
the moment the cable goes in, keeping everything recorded until then.
Unplug it to record. The generated signal, which needs no one wearing the
device, still runs while it charges.

A full charge lasts about a day of streaming, roughly 25 hours, at 250 or
500 samples per second. That is an estimate from the battery's voltage
over two hours of streaming on one pre-production unit, not a run from
full to empty. The charging time comes from the same unit. A number
measured before production says so until it has been measured on a
shipping unit.

## Turning it on

The switch on the edge. Off is off: the device draws nothing and does not
advertise.

## Wearing it

The electrodes have to touch skin, not hair. Part the hair where each one
sits and press the device down until the electrodes are against the
scalp. The strap holds it there. It should feel firm and not tight.

Contact is most of the quality of a recording. If a channel is noisy, it
is almost always contact and almost never the device. Lift it, part the
hair again, and press it back down.

The Command Center can turn on lead-off detection, which tells you which
electrodes the device believes are attached. It passes a very small
current to do that, so it is off unless you ask for it.

## What the light means

One light, one language, and you choose how much of it you want to see.
By default the light is dark, and it says only the two things that matter
when no screen is near: the battery is low, or the device failed its
start-up check. A blink means the same thing whichever setting you choose.

| Light | What it means | Shown when |
|---|---|---|
| Two blinks, then a pause | the battery is below twenty percent; it stops above twenty five, or on the charger | always, unless you chose silent |
| Three blinks, then a pause | the device failed its start-up check | always, unless you chose silent |
| Lit, with a short dark wink once a second | this is the device your software just asked to identify itself | always, for as long as you asked |
| A slow blink, once a second | on, waiting to be connected | verbose only |
| Steady | connected | verbose only |
| A brief pulse every two seconds | streaming | verbose only |
| Blinking quickly | an update is being written | verbose only |

The three settings are silent, reserved, and verbose. Reserved is the
default and shows the first two rows. Verbose shows everything, which is
useful while you learn the device or debug a connection. Silent shows
nothing at all, not even low battery, for someone who wants a dark device
on a sleeping head. Your software sets it, and the device remembers it
across power cycles; the Command Center has it under the device's settings.

When several things are true the light shows the most important: a failed
check, then low battery, then an update, then streaming, connected, and
waiting. Three blinks means the device could not bring up its own front
end. It still connects, so the Command Center can tell you what it found.

## Connecting

Turn it on, open the Command Center, and connect. The first time, your
computer will pair with it. After that it connects without pairing again,
whenever you choose it.

The link is encrypted, and everything except the device's own identity
requires that encryption. Pairing is the kind with no code to type,
because the device has no display and no buttons to type one on. That
stops anybody listening from reading your recording. It does not stop
somebody who is physically present at the moment you first pair, which is
the honest limit of a device with no screen.

The device remembers four computers. A fifth replaces the one you have
not used for longest.

## Several devices at once

One computer can stream from two devices at once at 250 samples per
second each. That was verified for an hour on one laptop, with no sample
lost from either device.

At 500 or 1000 samples per second, stream from one device per computer.
In a test with two devices at 500, one of them could not get all of its
samples through. It marked the ones it could not send as gaps, so the recording
showed exactly where they were missing.

## Its name

The device can carry your name and an adjective, and it shows them to
every computer and phone that scans for it: Ada's Blue IntoMind One. With
only a name it is Ada's IntoMind One, with only an adjective Blue IntoMind
One, and with neither it is IntoMind One. The Command Center sets both
under the device's settings, and the device keeps them across power
cycles. A new name shows in scans once the computer that set it lets go
of the device.

The whole name is at most 29 bytes, which is what a scan list can show,
so it is never cut short. Plain English letters, digits and spaces are
one byte each. Accented letters and other scripts take two to four, and
the Command Center counts them as you type.

When two devices near your computer share a name, your computer numbers
the later ones: Ada's IntoMind One 2. The number is your computer's, it
lasts as long as the list, and the device never holds it.

## A synthetic signal

The device can stream a signal it generates itself, in place of its
electrodes. It is for building and testing software against the device's
real timing without anyone wearing it, for demonstrations, and for
sharing a session that holds no one's brain data. The converter is off
while it runs, and it runs at 500 samples per second.

Everything made from it is marked. Every packet says it was generated,
and so does a recording made from it. The Command Center says so above
the trace for as long as it lasts.

The device runs one AI model at a time: the generator behind this signal,
or the foundation model that describes your own signal. While it
generates, there are no embeddings and no predictions, and it will not
start generating while either is on. Only the generator needs the
converter off. Turning your own recording's tokens back into signal needs
the converter and the foundation model, and works as it always does.

A small model on the device draws the encoder's description of the next
fifth of a second, channel by channel, and the reconstruction head turns
it back into signal. How close that comes to real EEG was measured on
19,459 windows from 37 recording studies the generator was not trained on:

| Measure | Synthetic | Real EEG |
|---|---|---|
| a linear classifier reading the encoder's embeddings, telling generated windows from real ones (area under the curve, 0.5 is chance) | 0.56, with a 95 percent interval of 0.51 to 0.63 | 0.38 to 0.58, one set of real studies against another |
| the same classifier over ten minutes without a reset | 0.53 to 0.55 in every minute | |
| power spectrum, 1 to 45 Hz | within 1.5 dB of real EEG | |
| coherence between channels, 8 to 13 Hz | 0.18 | 0.28 |

A score between 0.38 and 0.58 is what real EEG from a study the classifier
never saw gets, so on that classifier the synthetic signal passes for real
EEG. The generator was trained with the encoder in the loop, so that
result is partly by construction. The spectrum and the coherence are the
independent checks, and they are close but not equal.

It is not a recording of anyone and cannot stand in for one:

- It contains no events: no blinks, no muscle bursts, no spindles.
- A nonlinear classifier tells it from real EEG every time. It is close in
  the way the encoder's linear view sees it, and not beyond that.
- It varies less over time than one real person does, and above 45 Hz it
  is 3 dB from real EEG.

It is a demonstration signal, not data. Nothing should be trained or
validated on it.

## Updating it

Updates arrive through the Command Center and are written to the spare
half of the device's memory, so the copy you are running is never touched.
The device checks the signature before it will run anything, and if a new
version cannot start, the device goes back to the old one by itself. There
is no state in which an update leaves you with a device that does not
work.

## Care

Wipe the electrodes with a damp cloth after use and let them dry. They are
gold plated: no solvents, no abrasives, nothing that would take the
plating off.

Do not submerge the device. It is not sealed.

Store it somewhere dry. If you are not going to use it for months, charge
it first: a lithium cell left flat for a long time does not recover.

## If something is wrong

| What you see | What to try |
|---|---|
| It does not appear | check the switch, then charge it for an hour |
| One channel is noisy | contact. Lift, part the hair, press down |
| Every channel is noisy | you are probably on a charger. Unplug and record on the battery |
| It disconnects | distance, or something else on the same radio. Move closer |
| It connects but never answers, or a new feature is missing after an update | your computer is holding an older description of the device. Remove the device from your system's Bluetooth settings (on Linux, `bluetoothctl remove` with its address) and connect again |
| Three blinks | it failed its start-up check. Connect and read what the Command Center says |
| The Command Center says another program is listening | a second program on this computer subscribed to the device, so every packet arrives twice. The copies are dropped and your recording is intact. Close the other program if it should not be listening |

## What it is

| | |
|---|---|
| Channels | four, and a shared reference |
| Converter | Texas Instruments ADS1299-4, a twenty four bit biopotential front end; its registers can be read over the link for debugging |
| Radio | Raytac MDBT50Q-1MV2 module, a Nordic nRF52840 |
| Resolution | twenty four bits |
| Sample rates | 250, 500, or 1000 per second |
| Gain | up to twenty four |
| Noise floor | 0.14 microvolts root mean square with the inputs shorted at 250 samples per second, measured on a prototype of this design |
| Link | Bluetooth Low Energy, encrypted and bonded |
| Battery | a single rechargeable lithium polymer cell, charged over USB-C |
| Processing | on the device: a high-pass, a low-pass, and notch bands, on from the first use with a sensible default; the stream always says what produced it |
| Embeddings | the model's description of each four second window, sent to your computer on request in two forms: one vector for training heads, and the per-slice vectors that turn back into signal for generating it |
| The light | one status light with three settings: silent, reserved (the default), verbose; an identify blink on request |
| Name | yours to set: a name and an adjective, composed with the product's name, at most 29 bytes in all |
| Synthetic signal | a generated stream in place of the electrodes, at 500 samples per second, marked as generated wherever it goes |

## What the IntoMind One supports

The protocol is one contract for every IntoMind device, and no device
does all of it. This is what the IntoMind One answers to.

| Operation | IntoMind One |
|---|---|
| stream, rate, gain, input mode, contact detection, time sync, epoch reset | yes |
| battery and charger state | yes |
| boot record and self-confirmation | yes |
| updates over the air, signed | yes |
| the model, heads, predictions | yes |
| the processing chain: catalog, read, set, clear, restore | yes |
| where the model's input comes from | yes |
| the bias drive, set and read | no: its bias output reaches a pad and no further |
| the light: its setting read and set, and identify | yes |
| the converter's registers, read for debugging | yes, while not streaming |
| embeddings: the window embedding and the tokens, on request | yes |
| how often the model describes a window, read and set | yes |
| its name, read and set | yes |
| a synthetic signal | yes, at 500 samples per second |

The device carries a small neural network that turns four seconds of
signal into a compact description of it. See [the model](model.html).
