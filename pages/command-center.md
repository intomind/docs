---
title: Command Center
description: The Command Center app for the IntoMind One: install and run it, connect, watch the signal, record, export, use the model, and set up the device, in your own browser.
---

# Command Center

The Command Center is the app for using an IntoMind One from your computer. It runs a small server on your computer and shows its page in your browser, where you connect to the device, watch the signal, record, and export.

```sh
git clone https://github.com/intomind/commandcenter
cd commandcenter
pip install 'intomind[analysis]' aiohttp
python3 hub.py
```

Then open http://localhost:8080. It needs Python 3.11 or newer. The page also works with no device connected, so you can review recordings anywhere. On Linux, `./install-launcher.sh` adds it to your applications.

## What it does

- Lists the devices it hears and connects only the one you pick. It shows the device's firmware, channels and protocol version.
- Shows the live signal, and which electrodes are in contact when lead-off detection is on.
- Records, with markers or with cued protocols such as eyes open and closed, blinks, jaw clenches and eye movements.
- Reads recordings back, runs analyses on them, and exports them.
- Selects a head on the device and shows its predictions, sets how often the model runs, and saves the model's embeddings to a file for training heads.
- Sets the status light and the device's name, and makes the device identify itself.
- Says above the trace whenever the signal does not come from the electrodes, and when another program on the computer is also listening to the device.

The page has three levels. Basic shows every setting and lets you change a few everyday ones. Intermediate also lets you change the device's settings and its processing chain, and shows the ADC's registers. Advanced also lets you change the signal source and the analysis settings.

## Recordings

Recordings are saved in the `captures` folder inside the Command Center's folder, and exports in `exports`. A recording holds its samples, its events, and a record of how it was made: the device and its firmware, its settings, the processing chain, whether the signal was measured or generated, and where any gaps are. Checksums are written last, so a recording that stopped partway is never mistaken for a complete one.

## Exports

| Format | |
|---|---|
| BDF | 24-bit biosignal format, every value kept |
| EDF | the older 16-bit format, rounded to 16 bits |
| npz | NumPy arrays |
| CSV and TSV | text tables |
| MATLAB | version 7.3 files, every value kept |

Each export reports whether every value came out exactly as recorded, and if not, the largest error in microvolts. A recording whose checksums do not match is not exported. The Command Center uses the Python API's exporters, so a file exported here matches one exported from a script.

In BDF and EDF every sample stays at the time it was recorded. Where samples were lost, the file fills the hole with the lowest value it can store and labels it `BAD_ACQ_SKIP`, which MNE reads as a gap, and the page says how many samples it filled. A program that does not know the label shows a hole as a flat line at the bottom of the channel. These files are made of whole blocks of about a second, and the last block is completed after the last sample with the same filler under the same label, so no recorded sample is cut. The page says how many filler samples that took. Zero is not used, because it would make every recorded sample in an EDF file less precise. The electrode-off flags recorded with each sample are kept in npz and MATLAB exports only.

## It answers only your computer

The server listens only on your own computer, and it refuses requests from web pages on other sites, so a page you visit cannot reach it. The page loads nothing from the internet.

## License

Free software under the GNU Affero General Public License, version 3. For a commercial license, write to contact@intomind.com.
