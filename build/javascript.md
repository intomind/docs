---
title: JavaScript
description: The @intomind/sdk package for the IntoMind One: connect from a web page over Web Bluetooth, stream, send commands, run your own head, and decode the protocol in Node.
url: https://docs.intomind.com/javascript.html
---

# JavaScript

The `@intomind/sdk` package connects a web page to an IntoMind One over Web Bluetooth, with nothing for the user to install. It is written in TypeScript and also decodes the protocol in Node.

```sh
npm install @intomind/sdk
```

## Try it

With an IntoMind One switched on and unplugged, and a browser that has [Web Bluetooth](#browsers), you can connect to it from this page. Nothing is recorded, and nothing leaves your browser.

## Connect and stream

```ts
import { requestAndConnect } from "@intomind/sdk";

document.querySelector("#connect")?.addEventListener("click", async () => {
  const link = await requestAndConnect();              // the browser lists the devices nearby

  link.on((event) => {
    if (event.type === "samples") {
      const batch = event.batch;
      for (let row = 0; row < batch.rows; row++) {
        const uv = batch.microvolts(row, 0, link.info);  // channel 1, in microvolts
      }
    } else if (event.type === "gap") {
      console.log("lost", event.gap.samplesLost);        // null when the device restarted its count
    }
  });

  const answer = await link.request(link.session.startStream());
  if (!answer.ok) console.log("refused:", answer.statusName);
});
```

`requestAndConnect` must run from a click, on a page served over HTTPS or from `localhost`. The first connection pairs the device. `link.info` is what the device reported when it connected, and scaling a sample to microvolts needs it. Each batch carries the index and device time of its first sample, and a gap is announced before the batch that follows it.

Every batch says whether lead-off detection was running, in `batch.leadoffActive`, because a lead-off byte of zero is an attached electrode only when it was.

## Events

| Event | Carries |
|---|---|
| `samples` | samples, with `microvolts(row, channel, info)`, the first sample's index and device time, and whether the device generated them |
| `gap` | how many samples were lost, or `null` when the device restarted its count |
| `status` | battery, charger, whether USB is plugged in, and whether the device is streaming |
| `answer` | the device's answer to a command |
| `prediction` | a head's outputs for one window |
| `duplicate` | a packet that arrived twice and was dropped, because another program is listening to the device |

## Commands

`link.request` sends a command and waits for the device's answer. A command for something the device does not report is refused before it is sent.

```ts
import { protocol as P } from "@intomind/sdk";

const s = link.session;
await link.request(s.setRate(250));                     // refused while streaming
await link.request(s.setIndicator("verbose"));          // "silent", "reserved" or "verbose"
await link.request(s.identify(5));                      // the status light winks for five seconds
await link.request(s.setName("Ada", "Blue"));           // "Ada's Blue IntoMind One"
await link.request(s.setPipeline([P.highpass(0.5), ...P.mainsBands(60, 500), P.lowpass()], 500));
await link.request(s.setMode("synthetic"));             // the generated signal, at 500 per second
```

A stream started while USB is plugged in answers status 7: the device does not stream from its electrodes on USB power.

## Run your own head

Train a head in [Python](https://docs.intomind.com/python.html#the-model), then upload it from a page.

```ts
import { Transfer } from "@intomind/sdk";

const transfer = Transfer.head(link.session, 2, blob);   // slot 2: slot 1 holds the open sex head
await link.transfer(transfer, blob, ({ taken, total }) => console.log(`${taken} of ${total}`));
await link.request(link.session.selectHead(2));
await link.request(link.session.setPredictions(true));
```

## Browsers

Web Bluetooth is in Chrome on Windows, macOS, ChromeOS and Android, and in Edge and Opera on Windows and macOS. On Linux, Chrome needs `chrome://flags/#enable-web-bluetooth` turned on. Safari and Firefox do not have it, and neither does any browser on an iPhone or iPad.

## Node

Node has no Web Bluetooth, but everything except the connection works there. Pass the session the bytes your Bluetooth library receives, and write the bytes it returns.

```ts
import { Session, FILL } from "@intomind/sdk";

const session = new Session();
session.onDeviceInfo(deviceInfoBytes);                  // read from the Device Info characteristic
for (const event of session.onNotification(FILL.EEG_DATA, notificationBytes)) {
  // the same events as in a browser
}
const command = session.startStream();                  // write command.bytes to its characteristic
```

The package is tested against the protocol's conformance vectors, which the device's firmware generates from the code it runs.

## License

Free software under the GNU Affero General Public License, version 3. For a commercial license, write to contact@intomind.com.
