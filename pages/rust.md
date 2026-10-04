# Rust

```
cargo add intomind
```

The client does no input and no output. It is handed bytes that arrived
and it hands back bytes to send, which means it works over whatever
Bluetooth stack you already have, on whatever runtime you already use, and
it can be tested without either.

```rust
use intomind::{protocol::uuid_fill, Event, Session};

let mut session = Session::new();
session.on_device_info(&read(uuid_fill::DEVICE_INFO)?)?;

let command = session.start_stream();
write(command.characteristic, &command.bytes, command.with_response)?;

for event in session.on_notification(uuid_fill::EEG_DATA, &notification) {
    match event {
        Event::Samples(batch) => {
            let info = *session.info()?;
            for row in 0..batch.rows() {
                let uv = batch.microvolts(row, 0, &info);
            }
        }
        Event::Gap(gap) => {
            // Written down, never smoothed over. `samples_lost` is None
            // for a re-base, whose extent is not a number.
        }
        Event::Duplicate { .. } => {
            // A packet that arrived twice, dropped: another program on
            // this computer is listening to the device.
        }
        _ => {}
    }
}
```

## The crates

| | |
|---|---|
| `intomind` | a device as a state machine, over any transport |
| `intomind-protocol` | the wire, and nothing else. `no_std`, no dependencies |
| `intomind-capture` | what a recording is on disk |
| `intomind-model` | the encoder, `no_std`, allocating nothing |

`intomind-protocol` and `intomind-model` are the crates the device
firmware itself builds. The wire and the arithmetic are the same by
construction rather than by agreement.

## Capabilities

```rust
use intomind::protocol::device_info::capability;

if session.can(capability::MODEL) { /* ... */ }
session.set_leadoff(true)?;   // refused unless the device claims it
```

## Processing on the device

A device that claims the processing chain preprocesses its own signal, and
the chain in force is readable at any time. A chain is checked here, with
the device's own rules from `intomind-pipeline`, before anything is sent.

```rust
use intomind::protocol::pipeline::{kind, Chain, Stage};

let mut chain = Chain::NATURAL;
chain.push(Stage::one(kind::HIGH_PASS, 5))?;       // 0.5 Hz, in tenths
chain.push(Stage::two(kind::NOTCH, 580, 620))?;    // 58 to 62 Hz
chain.push(Stage::one(kind::LOW_PASS, 0))?;        // automatic corner
let command = session.set_pipeline(&chain, 500)?;  // refused with its reason if it cannot run at 500
let read = session.pipeline()?;                    // the answer decodes with pipeline::PipelineState
```

## The light, the registers, and embeddings

```rust
use intomind::embeddings::{Assembler, Form};
use intomind::protocol::control::indicator;

session.set_indicator(indicator::VERBOSE)?;             // silent, reserved, verbose
session.identify(5)?;                                   // the light winks for five seconds
let regs = session.converter_registers()?;              // answer decodes with control::ConverterRegisters
let ask = session.set_embeddings(Some(Form::Both))?;    // the window embedding and the tokens
let mut windows = Assembler::new(4, 20, Form::Both);    // channels, tokens per channel
// for each Event::Embedding(e): if let Some(w) = windows.feed(e) { ... one whole window ... }
```

`Assembler` returns a window when its last piece arrives: the embedding a
head consumes, the tokens generation starts from, both quantized exactly
as the device's heads receive them.

## Its name, the model's cadence, and a synthetic signal

```rust
use intomind::protocol::control::mode;

let ask = session.set_name("Ada", "Blue", "IntoMind One")?;   // refused unless the whole fits 29 bytes
let labels = intomind::display_names(&["Ada's IntoMind One", "Ada's IntoMind One"]);
// ["Ada's IntoMind One", "Ada's IntoMind One 2"]: the number is the host's
let every_minute = session.set_model_interval(60)?;         // 0 is every window it can
let synthetic = session.set_mode(mode::SYNTHETIC)?;         // the device generates the signal
// every Event::Samples(batch) it sends has batch.synthetic set
```

## The timebase

Device time onto host time is a line through several exchanges, and the
fit refuses what it cannot measure. One exchange fixes an offset and
claims no rate. A skew beyond a thousand parts per million is not two
crystals disagreeing, and a slope drawn through a stalled exchange is not
a measurement, so both are dropped and the offset is kept.

```rust
let mut tb = Timebase::new(info.time_tick_hz);
tb.observe(Exchange { before, after, device_ticks });
tb.host_time(sample_device_time);
```
