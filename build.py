"""Turn the Markdown in pages/ into the site in build/.

No dependencies, on purpose. Every layer between the text and the page is
a layer that can stop working, and this has to be buildable in ten years.

Some pages are assembled from the repositories they document, so that a
released version and its documentation cannot disagree about what the
software does. Those pages say where they came from.
"""
from __future__ import annotations

import html
import os
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAGES = HERE / "pages"
BUILD = HERE / "build"

SITE = "docs.intomind.com"

#: Where the protocol's documents are read from: the folder
#: INTOMIND_PROTOCOL_DIR names, or ~/.config/intomind/protocol, where the
#: maintainers keep them. Nobody's directory layout is written here.
PROTOCOL_DIR = pathlib.Path(os.environ.get("INTOMIND_PROTOCOL_DIR", "~/.config/intomind/protocol")).expanduser()

#: Pages assembled from elsewhere. Each is (destination, source, title,
#: credit). The source is a file in PROTOCOL_DIR; the credit is what the
#: page says about where it came from. A missing source is reported rather
#: than silently skipped, because a page that quietly stops being
#: generated is a page that goes stale.
ASSEMBLED = [
    ("protocol.md", "intomind-ble-protocol-v1.4.md",
     "The protocol", "the protocol contract the firmware and every host implement"),
    ("protocol-1-3.md", "intomind-ble-protocol-v1.3.md",
     "The protocol, 1.3", "version 1.3 of the protocol contract"),
    ("protocol-1-2.md", "intomind-ble-protocol-v1.2.md",
     "The protocol, 1.2", "version 1.2 of the protocol contract"),
    ("protocol-1-1.md", "intomind-ble-protocol-v1.1.md",
     "The protocol, 1.1", "version 1.1 of the protocol contract"),
    ("protocol-1-0.md", "intomind-ble-protocol-v1.0.md",
     "The protocol, 1.0", "version 1.0 of the protocol contract"),
]

#: The contract grows by addition, one document per version, newest first.
VERSIONS = [("protocol.html", "1.4"), ("protocol-1-3.html", "1.3"),
            ("protocol-1-2.html", "1.2"), ("protocol-1-1.html", "1.1"),
            ("protocol-1-0.html", "1.0")]

NAV = [
    ("index.html", "Start"),
    ("device.html", "The device"),
    ("command-center.html", "Command Center"),
    ("python.html", "Python"),
    ("rust.html", "Rust"),
    ("javascript.html", "JavaScript"),
    ("model.html", "The model and heads"),
    ("protocol.html", "The protocol"),
    ("safety.html", "Safety and care"),
]

STYLE = """
:root { color-scheme: light dark; --ink: #16181d; --paper: #fbfbf9;
        --quiet: #5c6068; --rule: #dcdcd6; --link: #1a4fa0; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e6e6e1; --paper: #16181d; --quiet: #9aa0a8;
          --rule: #2d3138; --link: #8fb4f0; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
       font: 16px/1.65 "Noto Sans", system-ui, -apple-system, "Segoe UI", Roboto, Ubuntu, "Helvetica Neue", Arial, sans-serif; }
header { border-bottom: 1px solid var(--rule); }
nav { max-width: 62rem; margin: 0 auto; padding: 1rem 1.5rem;
      display: flex; flex-wrap: wrap; gap: 0 1.25rem; align-items: baseline; }
nav .mark { font-weight: 600; letter-spacing: 0.02em; margin-right: 0.5rem; }
nav a { color: var(--quiet); text-decoration: none; font-size: 0.92rem; }
nav a:hover, nav a.here { color: var(--ink); }
main { max-width: 46rem; margin: 0 auto; padding: 2.5rem 1.5rem 5rem; }
h1 { font-size: 2.1rem; line-height: 1.2; margin: 0 0 1.5rem; }
h2 { font-size: 1.4rem; margin: 2.5rem 0 0.75rem; }
h3 { font-size: 1.1rem; margin: 2rem 0 0.5rem; }
p, li { max-width: 40rem; }
a { color: var(--link); }
code, pre { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
            font-size: 0.86em; }
code { background: color-mix(in srgb, var(--rule) 45%, transparent);
       padding: 0.1em 0.3em; border-radius: 3px; }
pre { background: color-mix(in srgb, var(--rule) 35%, transparent);
      padding: 1rem 1.15rem; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; margin: 1.25rem 0; width: 100%; }
th, td { text-align: left; padding: 0.45rem 0.8rem 0.45rem 0;
         border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-weight: 600; }
blockquote { margin: 1.25rem 0; padding-left: 1rem;
             border-left: 3px solid var(--rule); color: var(--quiet); }
footer { border-top: 1px solid var(--rule); color: var(--quiet);
         font-size: 0.85rem; }
footer div { max-width: 46rem; margin: 0 auto; padding: 1.5rem; }
.source { color: var(--quiet); font-size: 0.85rem; font-style: italic; }
"""


def inline(text: str) -> str:
    """The small marks, after escaping. Order matters: code first, so a
    backtick span is never reinterpreted."""
    out, at = [], 0
    for m in re.finditer(r"`([^`]+)`", text):
        out.append(emphasis(html.escape(text[at:m.start()])))
        out.append(f"<code>{html.escape(m.group(1))}</code>")
        at = m.end()
    out.append(emphasis(html.escape(text[at:])))
    return "".join(out)


def emphasis(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def render(md: str) -> str:
    """Markdown, as much of it as this site uses and no more."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(block)) + "</code></pre>")
            continue
        if line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        if m := re.match(r"(#{1,4}) +(.*)", line):
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue
        if line.startswith("> "):
            block = []
            while i < len(lines) and lines[i].startswith("> "):
                block.append(lines[i][2:])
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(block))}</p></blockquote>")
            continue
        if re.match(r"[-*] +", line) or re.match(r"\d+\. +", line):
            ordered = bool(re.match(r"\d+\. ", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and (re.match(r"[-*] +", lines[i]) or re.match(r"\d+\. +", lines[i])):
                items.append(re.sub(r"^(?:[-*]|\d+\.) +", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            continue
        if not line.strip():
            i += 1
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "```", "> ", "- ", "* ")):
            para.append(lines[i])
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def page(name: str, title: str, body: str, source: str | None = None) -> str:
    nav = "".join(
        f'<a href="{href}" class="{"here" if href == name else ""}">{label}</a>'
        for href, label in NAV)
    note = f'<p class="source">This page is {html.escape(source)}, so it cannot disagree with the software it describes.</p>' if source else ""
    if any(href == name for href, _ in VERSIONS):
        links = ", ".join(v if href == name else f'<a href="{href}">{v}</a>' for href, v in VERSIONS)
        note += (f'<p class="source">Each version adds to the one before it: {links}. '
                 'Version 1.1 restates the whole contract as it stood then.</p>')
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | {SITE}</title>
<style>{STYLE}</style>
<header><nav><span class="mark">IntoMind</span>{nav}</nav></header>
<main>{note}{body}</main>
<footer><div>IntoMind is a trademark of IntoMind, Inc. The software is free
software under the GNU Affero General Public License, version 3, with a
commercial license available at contact@intomind.com. The device is not a
medical device.</div></footer>
</html>
"""


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    missing = []
    for dest, source, title, credit in ASSEMBLED:
        src = (PROTOCOL_DIR / source).resolve()
        if not src.exists():
            missing.append(f"{dest}: {src} is not there")
            continue
        (PAGES / dest).write_text(src.read_text())
        print(f"  assembled {dest} from {src}")

    built = 0
    for md in sorted(PAGES.glob("*.md")):
        name = md.stem + ".html"
        text = md.read_text()
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), md.stem)
        source = next((c for d, _s, _t, c in ASSEMBLED if d == md.name), None)
        (BUILD / name).write_text(page(name, title, render(text), source))
        built += 1

    for href, label in NAV:
        if not (BUILD / href).exists():
            missing.append(f"{href} is in the navigation and was not built ({label})")

    print(f"{built} pages into {BUILD}")
    if missing:
        print("\nnot right yet:")
        for m in missing:
            print(f"  {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
