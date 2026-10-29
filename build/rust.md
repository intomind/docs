---
title: Rust
description: The intomind Rust crates for the IntoMind One: a client that works over any Bluetooth stack and runtime, with commands, processing, embeddings, head uploads, and the timebase.
url: https://docs.intomind.com/rust.html
---

# Rust

The `intomind` crate is a client for the IntoMind One that does no input or output of its own. You give it the bytes your Bluetooth stack received, and it returns events and the bytes to send. It works with any Bluetooth library and any async runtime, or none.

```sh
cargo add intomind
```

| Crate | |
|---|---|
| `intomind` | the client, with the timebase and head uploads |
| `intomind-protocol` | the protocol's messages as code. `no_std`, with no dependencies |
| `intomind-pipeline` | the device's processing chain, so a chain can be checked before it is sent |
| `intomind-model` | the encoder's arithmetic, as the device does it. `no_std`. Enable it with `--features model` |
| `intomind-capture` | recordings: read as every IntoMind program writes them, and exported in six formats |

## Connect and stream

Your Bluetooth library reads Device Info once, writes the commands the session builds, and passes every notification to the session.

```rust
use intomind::protocol::uuid_fill;
use intomind::{Event, Session};

fn stream(stack: &mut impl Stack) -> Result<(), Box<dyn std::error::Error>> {
    let mut session = Session::new();
    session.on_device_info(&stack.read(uuid_fill::DEVICE_INFO)?)?;
    let info = *session.info()?;

    let start = session.start_stream();
    stack.write(start.characteristic, &start.bytes, start.with_response)?;

    while let Some((characteristic, bytes)) = stack.next_notification() {
        for event in session.on_notification(characteristic, &bytes) {
            match event {
                Event::Samples(batch) => {
                    for row in 0..batch.rows() {
                        let uv = batch.microvolts(row, 0, &info); // channel 1, in microvolts
                        println!("{} {uv:.2}", batch.index + row as u32);
                    }
                }
                // None when the device restarted its count.
                Event::Gap(gap) => println!("gap {:?}", gap.samples_lost),
                Event::Duplicate { .. } => {} // another program is listening: dropped
                _ => {}
            }
        }
    }
    Ok(())
}

/// What your Bluetooth library provides.
trait Stack {
    fn read(&mut self, fill: u16) -> Result<Vec<u8>, Box<dyn std::error::Error>>;
    fn write(&mut self, fill: u16, bytes: &[u8], with_response: bool) -> Result<(), Box<dyn std::error::Error>>;
    fn next_notification(&mut self) -> Option<(u16, Vec<u8>)>;
}
```

`intomind::protocol::uuid128(fill)` gives each characteristic's full UUID.

## Commands

Every command is checked against what the device reported, and one the device cannot carry out returns an error rather than bytes.

```rust
use intomind::protocol::control::{indicator, mode};
use intomind::protocol::device_info::capability;

if session.can(capability::LEADOFF) {
    let command = session.set_leadoff(true)?;
}
// Every batch then says whether detection was running, in `batch.leadoff_active`:
// a lead-off byte of zero is an attached electrode only when it was.
let verbose = session.set_indicator(indicator::VERBOSE)?;          // silent, reserved, verbose
let identify = session.identify(5)?;                               // the status light winks for five seconds
let name = session.set_name("Ada", "Blue", "IntoMind One")?;       // refused unless it fits 29 bytes
let synthetic = session.set_mode(mode::SYNTHETIC)?;                // the generated signal
```

## Processing on the device

```rust
use intomind::protocol::pipeline::{kind, Chain, Stage};
use intomind::{Command, Error, Session};

fn my_chain(session: &Session) -> Result<Command, Error> {
    let mut chain = Chain::NATURAL;                    // no stages
    chain.push(Stage::one(kind::HIGH_PASS, 5))?;       // 0.5 Hz, in tenths of a hertz
    chain.push(Stage::two(kind::NOTCH, 580, 620))?;    // 58 to 62 Hz
    chain.push(Stage::one(kind::LOW_PASS, 0))?;        // the automatic corner
    session.set_pipeline(&chain, 500)                  // refused, with the reason, if it cannot run at 500
}
```

## Embeddings

```rust
use intomind::embeddings::{Assembler, Form};

let ask = session.set_embeddings(Some(Form::Window))?;
let mut windows = Assembler::new(4, 20, Form::Window);  // channels, tokens per channel
// for each Event::Embedding(part): if let Some(window) = windows.feed(part) { ... }
```

## Run your own head

A transfer tells you what to write, and you tell it what the device answered.

```rust
use intomind::{Step, Transfer};

let mut transfer = Transfer::head(&session, 2, &blob)?;   // slot 2: slot 1 holds the open sex head
loop {
    match transfer.step(&blob) {
        Step::Send(command) => {
            write(&command);
            transfer.on_answer(&update_answer()?, &blob)?;
        }
        Step::Data { from, to, .. } => {
            write_data(&blob[from..to]);
            transfer.sent(to - from);
        }
        Step::Verified(_) => break,
    }
}
```

Then select it with `session.select_head(2)` and turn predictions on with `session.set_predictions(true)`. Heads are trained in [Python](https://docs.intomind.com/python.html#the-model).

## The timebase

`Timebase` maps device time onto your computer's clock from time exchanges with the device. One exchange gives the offset between the clocks, and a rate needs at least three.

```rust
use intomind::{Exchange, Timebase};

let mut timebase = Timebase::new(info.time_tick_hz);
timebase.observe(Exchange { before, after, device_ticks });
let seconds = timebase.host_time(device_ticks);
```

The crates are tested against the protocol's conformance vectors, which the device's firmware generates from the code it runs.

## Recordings and exports

`intomind::capture` reads the recordings the Command Center and the Python API make, and exports them in the same six formats, with the same rules and the same summary. A BDF, EDF, CSV or TSV file exported here is the same file, byte for byte, as one exported from Python, and an NPZ or MATLAB file holds the same arrays.

```rust
use intomind::capture::{export, recording::Collection};

let recordings = Collection::open(Collection::default_dir());
let summary = export::export(&recordings, "my-recording", "bdf", None)?;   // also "edf", "npz", "csv", "tsv" and "mat"
println!("{} samples, largest error {} µV", summary["samples"], summary["max_error_uv"]);

let recording = recordings.load("my-recording")?;                       // refused if its checksums do not match
let ch1 = recording.uv(0)?;
```

`Collection::default_dir()` is the folder the Python API uses. An export with no path goes in `exports` beside it. What every file holds and promises is on [Recordings and files](https://docs.intomind.com/files.html).

## License

Free software under the GNU Affero General Public License, version 3. For a commercial license, write to contact@intomind.com.
