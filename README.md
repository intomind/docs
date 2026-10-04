# docs.intomind.com

The documentation for everything IntoMind publishes, and the manual for
the device.

Plain Markdown in `pages/`, turned into plain HTML by one script with no
dependencies. No framework, no build toolchain, no package manager. The
reason is the same reason the capture format is flat files: somebody has
to be able to build this in ten years, and every layer between the text
and the page is a layer that can stop working.

```
python3 build.py            # writes build/
python3 -m http.server -d build 8000
```

Some pages are assembled from the documents they publish, so that a
released version and its documentation cannot disagree. `build.py` names
which, and says so on the page. The protocol's documents are read from the
folder `INTOMIND_PROTOCOL_DIR` names, or `~/.config/intomind/protocol`.

```
python3 check.py            # builds, then checks
```

`check.py` resolves every name the Python examples show against the
installed instrument library, so it needs that library importable. It
refuses to pass if it could not check a single name, because a gate that
cannot fail is not a gate. It also reads every page and every tracked file
for words nothing published may carry. Those words are themselves private,
so they are kept on the maintainers' machines, in the file
`INTOMIND_PRIVATE_WORDS` names or `~/.config/intomind/private-words.tsv`,
and the check fails without them. The JavaScript and Rust examples are compiled
in the SDK repository, where the types are.

## How the site is published

GitHub Pages serves `build/` exactly as it is committed: every push to
`main` publishes it (`.github/workflows/pages.yml`). Nothing is built on
GitHub, so what was checked here is what goes out.

## License

Free under the GNU Affero General Public License, version 3. We also
license it commercially, on fair terms shaped by your use case: write to
contact@intomind.com. See `LICENSING.md`, and `CONTRIBUTING.md` before a
first pull request.
