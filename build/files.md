---
title: Recordings and files
description: What a recording is, what each export format holds, how gaps and the last block are written, what every export reports, and the rule that versions follow.
url: https://docs.intomind.com/files.html
---

# Recordings and files

Every recording made with the Command Center, the Python API or the Rust crates is kept the same way, and every export follows the same rules, whichever program asked for it. The Rust crates and the JavaScript package read the same recordings and write the same six files, byte for byte or array for array, as [Rust](https://docs.intomind.com/rust.html#recordings-and-exports) and [JavaScript](https://docs.intomind.com/javascript.html#recordings-and-exports) show. This page is the contract: what a recording is, what each file holds, and what will not change.

## A recording

A recording is a set of files that share one name, in the recordings folder (`captures` by default).

| File | What it holds |
|---|---|
| `name.npz` | The samples, as the converter's own counts for every channel, with each sample's index, device time and host time, and the lead-off byte and gap mark that arrived with it. |
| `name.meta.json` | The manifest: when the recording was made, the device and its firmware, its settings, the processing chain, whether the signal was measured or generated, where any gaps are, the electrode positions when they were given, and a version number for the manifest itself. |
| `name.events.json` | The markers placed during the recording, each at its device time. |
| `name.sha256` | A checksum of every file above, written last. |

Four things hold for every recording:

- The checksums are written last. A recording without them stopped partway, and no export or analysis treats it as complete.
- A recording is never rewritten. A fact learned later, such as where the electrodes were, is kept in a separate file beside it, so what the instrument recorded and what a person added afterwards stay distinguishable.
- A manifest field is never renamed, and every older manifest version stays readable. New fields are added and old ones keep their meaning.
- The samples are the record. Every other file, including every export, is derived from them and can be made again.

## Exports

```python
from intomind import export

export.export("my-recording", "bdf")       # also "edf", "npz", "csv", "tsv" and "mat"
```

Six formats, one call. Every one refuses a recording whose checksums do not match. Every one reports the same six things, `label`, `path`, `format`, `channels`, `samples` and `sample_rate_hz`, and whether every value came out exactly as recorded. Where a value could not, `lossy` is true and `max_error_uv` is the largest error in microvolts.

| Format | What it holds |
|---|---|
| npz | Microvolts per channel as `ch1_uv` and so on, with each sample's index, device time, host time, lead-off byte and gap mark, and the manifest. Every value as recorded. |
| csv and tsv | One header row, then one row per sample: `host_time_s`, `device_time`, and a microvolt column per channel. The rows are the samples, in order, and nothing is inserted where samples were lost. Both clocks are there so that a gap shows in the text. |
| mat | MATLAB version 7.3, which needs `h5py`. The microvolts as `uv`, the manifest as one line of text, and the per-sample arrays. Every value as recorded. |
| bdf | BDF+, 24 bits per sample. At 24 bits the step is narrower than one converter count on any recording that does not span the whole converter, so the values are what was recorded and the error is measured, not assumed. |
| edf | EDF+, 16 bits per sample, and therefore lossy by construction. `max_error_uv` says by how much. The step depends on the signal's own range in the file, not on its offset. |

A recording the device generated is marked as generated wherever it goes: the columns are named `ch1_synthetic_uv`, the MATLAB matrix `synthetic_uv`, and the manifest says so.

In a MATLAB file written by 1.4.1 or earlier, the manifest opens as a column of characters. `jsondecode(S.manifest_json(:)')` reads it from a file of any version.

## Time in BDF and EDF files

In BDF and EDF, every sample is written at the time it was recorded, counted from the sample index the device gave it. This is what the files promise, and what changed in 1.4.1.

- **A hole** holds one placeholder for every sample that was lost, so everything after it stays where it belongs, under a `BAD_ACQ_SKIP` annotation over exactly the hole. That is the label MNE gives a hole in its own files: it filters each side of a hole separately, rejects an epoch that overlaps one, and returns the hole as NaN when asked with `get_data(reject_by_annotation="NaN")`. A reader that does not know the label shows a hole as a flat line.
- **The placeholder** repeats the last recorded value, which is what MNE's own writer puts in the block it completes. These formats hold whole numbers, so NaN cannot be written. A value apart from the signal, such as the lowest number the file can store, is a step thousands of microvolts deep that a filter or a spectrum takes for signal. The last value adds no step and costs no precision, because it is already inside the signal's range.
- **The last block.** The files are whole blocks of about a second, and the last block is completed after the last sample with the same placeholder under the same label, so no recorded sample and no marker is left out. Before 1.4.1, the samples after the last whole block were left out of the file and counted in `samples_dropped`. That key is still reported, and is now 0.
- **A restart.** A recording whose sample count starts again within its first second begins with samples from before the recording started. The file starts at the restart, and `samples_before_restart` says how many samples were left out. A count that steps back later is a break whose length is not known, and the file is refused rather than given a timeline the recording does not have.
- **The sample rate** is kept exactly. The device's measured rate is rarely a whole number, and these formats need a whole number of samples per block, so the block's duration carries the remainder.
- **The range** each signal states in the header is rounded outward, so its lowest and highest samples are never clipped.
- **Markers** are written as annotations at their recorded times.

What these two exports report, beyond the six things every export reports:

| Key | Meaning |
|---|---|
| `gaps` | how many holes the file has |
| `samples_filled` | how many placeholders fill them |
| `tail_filled` | how many placeholders complete the last block |
| `samples_before_restart` | how many samples before a restart were left out |
| `samples_dropped` | how many recorded samples were left out of the file, 0 since 1.4.1 |
| `continuity` | `+C` for a continuous file |
| `bits`, `quantum_uv`, `lsb_uv` | the sample width, the file's step in microvolts, and the recording's own step |

## Lead-off in files

Lead-off detection reports which electrodes have come off, and it runs only when it is turned on. A lead-off reading of zero means every electrode was attached only while detection ran, so every file carries lead-off only where the recording says detection was running, and says so. On the IntoMind One each channel's bit is its positive electrode.

- npz and mat carry the lead-off byte for every sample and, beside it, whether detection was running at that sample.
- csv and tsv add a column per channel, `ch1_leadoff` and so on, with 1 where the electrode was off, 0 where it was attached, and empty where nothing was checking. The columns are present only when detection ran somewhere in the recording.
- bdf and edf label each stretch an electrode was off `BAD_LEADOFF` followed by the channel's label, which MNE treats as bad, and label the part of a recording where detection was off `LEADOFF_NOT_CHECKED`, written only when it ran for the rest.
- every export reports `contact`: `checked`, `partly checked`, `not checked`, or `not known` for a recording made before the flag was kept. bdf and edf also report `electrode_off_stretches`.

## Versions

The Python package, the Rust crates and the JavaScript package share one version number. Its minor digit follows the minor version of the protocol, so a package that speaks protocol 1.4 is a 1.4 release. Its last digit counts releases of the packages. A name that has been published, whether a function, a key in a summary, a column in a file or a field in a manifest, keeps its meaning in every later release. New names are added, old names are never removed or renamed. This site describes the released packages, and nothing newer.
