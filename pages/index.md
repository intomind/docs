# IntoMind One

A four channel EEG headset that streams your brain's own electrical
activity to a computer you own, over Bluetooth, and software you can read.

Everything on this site is about two things: the device, and the code that
talks to it. The code is free software. The recordings are yours and they
stay on your machine.

## Start here

| | |
|---|---|
| [The device](device.html) | what is in the box, how to wear it, what the light means |
| [Command Center](command-center.html) | the program that runs it, with nothing to set up |
| [Python](python.html) | the instrument library, for scripting and analysis |
| [Rust](rust.html) and [JavaScript](javascript.html) | the SDK, for building something of your own |
| [The model and heads](model.html) | the encoder on the device, and teaching it what you care about |
| [The protocol](protocol.html) | the wire, in full, for anyone writing their own client |
| [Safety and care](safety.html) | what this is not, and how to look after it |

## What it actually does

Four electrodes sit against your scalp. The device amplifies what they
pick up, converts it twenty four bits deep, timestamps every sample
against its own clock in hardware, and streams it. It filters only through
a chain you can read and change, a high-pass, a low-pass and mains notches
by default, and the stream always says which chain produced it. It does
not smooth, and it does not fill in anything it missed. If a sample
is lost, the recording says so, where, and how many.

That last part is the whole design. A recording you cannot trust is worse
than no recording, because you will draw a conclusion from it.

## What you need

A computer with Bluetooth Low Energy. The Command Center runs on it and
serves a page to your own browser. Nothing is sent anywhere, no account is
required, and it works with no network at all.

## The software is free software

The instrument library, the SDK, the Command Center and the open heads are
under the GNU Affero General Public License, version 3. Read them, change
them, build on them, ship what you make. A commercial license is available
if you want to build something closed: write to contact@intomind.com.

| | |
|---|---|
| [github.com/intomind/api](https://github.com/intomind/api) | the instrument library, `pip install intomind` |
| [github.com/intomind/sdk](https://github.com/intomind/sdk) | the SDK, `cargo add intomind` and `npm install @intomind/sdk` |
| [github.com/intomind/commandcenter](https://github.com/intomind/commandcenter) | the Command Center |
| [github.com/intomind/eeg-foundation-model-heads](https://github.com/intomind/eeg-foundation-model-heads) | open heads for the encoder on the device |
