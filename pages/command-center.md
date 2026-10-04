# Command Center

The program that runs the device. A local server and a page in your own
browser. Nothing is sent anywhere.

```
git clone https://github.com/intomind/commandcenter
cd commandcenter
pip install 'intomind[analysis]' aiohttp
python3 hub.py
```

Then open `http://localhost:8080`.

The page serves whether or not a device is connected, so you can go back
through recordings with no hardware present.

## What it does

- Connects to a device and shows what it is: its firmware, its channels,
  its rates, and what it says it can do.
- Shows the live signal, and contact quality when lead-off detection is on.
- Runs the cued protocols the instrument library provides, and records
  them with everything about how they were produced.
- Reads recordings back, runs the analyses on them, and exports them.
- Where a device carries a model, selects a head and shows what it
  predicts, and collects the model's embeddings from the live stream into
  a file for training heads or generating signal.
- Sets the device's light: silent, reserved, or verbose, and makes it
  identify itself with a blink.
- Names the device: your name and an adjective, shown composed as you type
  and counted against the 29 bytes a scan list can show.
- Sets how often the model describes a window, and shows how long one
  pass takes on the device.
- Says above the trace whenever the signal is not your electrodes: the
  converter's test signal, shorted inputs, or the device's synthetic
  signal.
- Lists the devices it hears and connects only the one you pick. Nothing
  connects by itself.
- Says when another program on this computer is also listening to the
  device. Each packet then arrives twice, and the copy is dropped.
- In Intermediate, reads the converter's registers in words, for debugging.

## It only listens to your own machine

The server refuses any request whose Host header is not localhost, and any
request or websocket whose Origin is a page somewhere else. That is not
paranoia: a page on the internet can otherwise reach a server running on
your machine, and read what it says, including over a websocket, which
ordinary cross origin rules do not cover.

## Exports

Six formats, and the Command Center calls the instrument library's
exporter rather than writing its own, so a file exported here is the same
file exported from a script.

| Format | What it is for |
|---|---|
| npz | numpy, lossless |
| BDF | twenty four bit biosignal format, lossless for this device |
| EDF | the older sixteen bit format, widely read, and lossy. It says so, with the error measured |
| csv and tsv | text, for anything that reads a table |
| MATLAB v7.3 | for MATLAB |

Whether a format was lossless for a given recording is measured rather
than claimed: the exporter reads what it wrote and compares.

## Recordings

They go to `~/.local/share/intomind/captures`, or wherever
`$INTOMIND_CAPTURES` points.

Each one is its samples, its events, and a manifest that says how it was
produced: the device, its firmware, its configuration, whether the signal
was measured or generated, where the gaps were, how the clocks were
fitted, and what software recorded it.
Checksums are written last, so a run that dies half way leaves something
that is visibly incomplete rather than something that looks finished and
is short.

## License

Free software under the GNU Affero General Public License, version 3. If
you run a modified copy as a service for other people, they can ask you
for your changes. A commercial license is available at
contact@intomind.com.
