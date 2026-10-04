# JavaScript

```
npm install @intomind/sdk
```

The same protocol, in TypeScript, for browsers and Node. In a browser it
uses Web Bluetooth, so a page can talk to a device with nothing installed.

```javascript
import { requestAndConnect } from "@intomind/sdk";

// The browser asks the user to pick a device. It must start from a click.
const link = await requestAndConnect();

link.on((event) => {
  if (event.type === "samples") {
    const uv = event.batch.microvolts(0, 0, link.info);
  }
  if (event.type === "gap") {
    // written down, never smoothed over
  }
});

await link.send(link.session.startStream());
```

A device that claims the processing chain preprocesses its own signal,
and the chain is checked here with the device's own rules before it is
sent:

```ts
import { protocol as P } from "intomind";

await link.send(link.session.setPipeline([P.highpass(0.5), ...P.mainsBands(60, 500), P.lowpass()], 500));
const state = P.decodePipelineState((await link.request(link.session.pipeline())).payload);
```

`link.info` is what the device said it is, read before anything was asked
of it. Scaling a count needs it, because the reference voltage and the
converter width are the device's to state and not this library's to
assume.

Pass `onEvent` to `requestAndConnect` instead if you need the events that
arrive while the link is still being set up. That callback cannot refer to
the link, because the link does not exist yet.

## The same rules as everywhere else

- What a device can do is the bits it reports, not a version number.
- A gap is announced before the samples that follow it, so anything
  writing samples down writes the break down first and can never splice.
- A loss carries an exact count. A break carries none, because zero
  missing samples is a different statement from an unknown extent.
- A packet that arrives twice is dropped and counted, and a `duplicate`
  event says so. It means another program on the same computer is
  listening to the device.
- Nothing assumes a channel count, a converter width, or a reference
  voltage. They come from the device.

## Held to the same vectors

The package is tested against `contract/conformance.json`, which the
device firmware emits from the codec it runs: 66 messages to decode and 56
to refuse. So is the Rust crate, and so is the Python library. An
implementation that drifts fails a test rather than a session.

One warning if you read that file yourself. It writes every 64-bit field
as a decimal string, because a device time runs past what a JSON number
holds exactly. Parse it with `BigInt`, not `Number`.

## The light, the registers, and embeddings

```ts
session.setIndicator("verbose");           // silent, reserved, verbose
session.identify(5);                       // the light winks for five seconds
session.converterRegisters();              // answer decodes with decodeConverterRegisters, describeAds1299Registers
session.setEmbeddings("both");             // the window embedding and the tokens
const windows = new EmbeddingAssembler(4, 20, "both");   // channels, tokens per channel
// for each event of type "embedding": const w = windows.feed(event.embedding); if (w) { ... one whole window ... }
```

## Its name, the model's cadence, and a synthetic signal

```ts
P.composeName("Ada", "Blue");              // "Ada's Blue IntoMind One"
P.nameFits("Beatrice", "Purple");          // false: 30 bytes, over the 29 a scan list shows
session.setName("Ada", "Blue");            // refused before sending if it would not fit
session.getName();                         // answer decodes with decodeNameParts
P.displayNames(["Ada's IntoMind One", "Ada's IntoMind One"]);   // the second becomes "Ada's IntoMind One 2"
session.setModelInterval(60);              // one window a minute; 0 is every window it can
session.modelInterval();                   // answer decodes with decodeModelInterval
session.setMode("synthetic");              // the device generates the signal, at 500 per second
// every batch it sends says so: event.batch.synthetic
```

The number `displayNames` adds to a shared name is the host's. The device
never holds it.

## Web Bluetooth

Works in Chrome and Edge on desktop and Android. Safari and Firefox do
not implement Web Bluetooth. The page must be served over HTTPS, or from
localhost, and the connection has to start from something the user
clicked.
