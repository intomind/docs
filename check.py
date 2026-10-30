"""Build the site and check it, in one command.

A documentation site rots quietly: a page drops out of the build, a link
points at something that was renamed, a heading stops being a heading
because a character changed. None of that raises an error on its own, so
it is checked here and the exit code says whether the site is sound.

The worst rot is an example that no longer works. Every name a Python
example shows is resolved against the installed library, so a rename
breaks this check rather than someone's first hour with the thing. The
JavaScript and Rust examples are not compiled here.

The site also loads nothing from anywhere else, and carries a copy of the
published JavaScript SDK for its interactive parts. Both are checked: a
page that fetched a font from a third party would tell that party who read
it, and a copy of the SDK that drifted from the published one would show
readers something the package does not do.
"""
from __future__ import annotations

import hashlib
import html
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE / "build"

#: The published @intomind/sdk 1.4.2, file by file, as npm serves it: every module
#: a browser loads (tarball sha1 edcf28ca7f4858847ea3fd37d6be1569a13c5221).
VENDORED = HERE / "assets" / "vendor" / "intomind-sdk-1.4.2"
VENDORED_SHA256 = {
    "capture/clock.js": "e1f3eb608760564df74a6729883e36d8b038baee1b4ec6187f4b4bcb7110bd4c",
    "capture/edf.js": "331dcf88638d0e8bb1c45ce362e431f21219d15598e9d13aada1d3b93a21f288",
    "capture/errors.js": "f6ff93d9899bf507ffba12de1281b0e85a08a3b5f3020d98e6e995d30bd32f89",
    "capture/export.js": "b0c8c5588cd040ee7f18c035917dbd00f1b41dd9b9fba875cc19b68643d728da",
    "capture/hdf5.js": "46eb49370e0a2dbc718fc5777e7f7359933fd2a530e00f997f79d6fa71c4cc74",
    "capture/index.js": "07df0cfb975db5412a89666ffe6c228d943d1c8744ab432518435942dd0b753f",
    "capture/montage.js": "a0d89ccfb1348c76f7220d4e3be3586553ae707af810a8283cf992b84b791b05",
    "capture/npy.js": "7e21cf08a9f4fe8a17786bfe848182a59ccea5e1328d82a335ef6f701486b20f",
    "capture/placement.js": "15c57873ad523f8d4eb9017b23843d7e1ee3288a1025235d537fc4026b2dda26",
    "capture/pyfmt.js": "37264029ba58973bed5b8b7b08e8f5436c3c7d1170b0ca9f979403cc873e5a48",
    "capture/pyjson.js": "d60c7fd0e471e8d596b8a5b5655bc3b22a7b35938b119a03ee1ae6ed32a73566",
    "capture/record.js": "61b3dd76bf611e4b3c9c94fa503784540e437df1abe1794b89e947330633a20f",
    "capture/recording.js": "15869e22884de1704ece152f475feef2151e113ae290b663c7de1e0fdf98dd50",
    "capture/unprintable.js": "fc6d2da92cfd479b084df36377b45a7a505940968d4496678853ed586e795a53",
    "capture/version.js": "aaeaee5e405a486d953b7f2c01a658e32bb6631495b478cda60d0b8d4f732cd9",
    "capture/zip.js": "34c049a494aff388e8fb37bb0cb85d70170ae2efa1d741ce933af042dcd2c149",
    "digest.js": "8e357d10ea895040331d94e4327a611d58ac3fde22c3b2fee2f74a9fdb38bf47",
    "index.js": "5833940a98f7fa8c7650be0f168ba9f4755e0833da425b17a03f6a87e4247fe3",
    "protocol.js": "d1e895c13730a625002461eef30c81546fa4976d59ca0d766e9d878ca2d51983",
    "session.js": "a6176ca817046717e28494f025fe73445e6d9f0790e7c18f74cdf6e759692175",
    "timebase.js": "308d5b6af89e23b59c94a367300f041cf4e98bbe80ac82fad7eab804802da478",
    "transfer.js": "052c394fc0e0a81d3851cac4febb0daa63432c029e47c2fe32da5deb4588485d",
    "web-bluetooth.js": "7ce58c37e11c588f0286fa3e363e846e8e9afb4e7792b36c074434c7c800eb9d",
}


def main() -> int:
    built = subprocess.run([sys.executable, str(HERE / "build.py")], cwd=HERE)
    problems: list[str] = []
    if built.returncode != 0:
        problems.append("the build itself reported a problem")

    pages = sorted(BUILD.glob("*.html"))
    if not pages:
        problems.append("nothing was built")

    ids = {f.name: set(re.findall(r' id="([^"]+)"', f.read_text())) for f in pages}
    sitemap = (BUILD / "sitemap.xml").read_text() if (BUILD / "sitemap.xml").exists() else ""
    llms = (BUILD / "llms.txt").read_text() if (BUILD / "llms.txt").exists() else ""
    for f in pages:
        text = f.read_text()
        m = re.search(r"<main[^>]*>(.*)</main>", text, re.S)
        body = m.group(1) if m else ""
        # Code blocks are not prose and are not Markdown. A backtick or a
        # pair of asterisks inside one is the code saying what it says.
        prose = re.sub(r"<pre[^>]*>.*?</pre>", "", body, flags=re.S)
        for pattern, why in [
            (r"^\s*#{1,4} ", "a heading that was not rendered"),
            (r"\|\s*---", "a table rule that was not rendered"),
            (r"&lt;(p|h1|h2|table|code)&gt;", "a tag that was escaped instead of rendered"),
            (r"\*\*", "emphasis that was not rendered"),
            (r"`[^`]+`", "a code span that was not rendered"),
            (r"<p>\s", "a wrapped bullet rendered as a paragraph"),
        ]:
            if re.search(pattern, prose, re.M):
                problems.append(f"{f.name}: {why}")
        for href, anchor in re.findall(r'href="/?([^":#]+\.html)(?:#([^"]+))?"', text):
            if not (BUILD / href).exists():
                problems.append(f"{f.name}: links to {href}, which is not there")
            elif anchor and anchor not in ids.get(href, set()):
                problems.append(f"{f.name}: links to {href}#{anchor}, which has no such section")
        for anchor in re.findall(r'href="#([^"]+)"', text):
            if anchor not in ids[f.name] and anchor != "content":
                problems.append(f"{f.name}: links to #{anchor}, which this page does not have")
        if "<title>" not in text:
            problems.append(f"{f.name}: no title")
        if not re.search(r'<meta name="description" content="[^"]{40,}">', text):
            problems.append(f"{f.name}: no description for search engines")
        if "\u2014" in text:
            problems.append(f"{f.name}: an em dash, which the public pages do not use")
        # The pages we write keep to the house style. The contract's own
        # documents are assembled as written and keep theirs.
        if '<p class="source">' not in text:
            words = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(code|pre)[^>]*>.*?</\1>", "", prose, flags=re.S)))
            if ";" in words:
                problems.append(f"{f.name}: a semicolon in the text, which the public pages do not use")
            # A product manual, not development notes: no qualifiers about
            # where a number was measured, and rates are per second.
            for pattern, why in ((r"pre-production|prototype|\bunit one\b|\bbench\b|\bour test", "development notes"),
                                 (r"\b(?:\d+|samples) a second\b", "a rate written as 'a second' rather than 'per second'")):
                if m := re.search(pattern, words, re.I):
                    problems.append(f"{f.name}: '{m.group(0)}', {why}")
        if 'class="anchor"' in text:
            problems.append(f"{f.name}: a link mark on a heading")
        # Nothing loads from another site: no script, style, font or image.
        for tag in re.findall(r"<(?:script|img|link|source|iframe|video|audio)\b[^>]*>", text):
            if 'rel="canonical"' in tag or 'rel="alternate"' in tag:
                continue
            if m := re.search(r'(?:src|href)="((?:https?:)?//[^"]+)"', tag):
                problems.append(f"{f.name}: loads {m.group(1)} from another site")
        if f.name != "404.html":
            url = "https://docs.intomind.com/" + ("" if f.name == "index.html" else f.name)
            if f"<loc>{url}</loc>" not in sitemap:
                problems.append(f"{f.name}: missing from the sitemap")
            if not (BUILD / (f.stem + ".md")).exists():
                problems.append(f"{f.name}: has no Markdown twin")
            if not f.name.startswith("protocol-1-") or f.name == "protocol-1-4.html":
                if f"/{f.stem}.md)" not in llms and f.name != "index.html" or (f.name == "index.html" and "/index.md)" not in llms):
                    problems.append(f"{f.name}: missing from llms.txt")

    problems += names_that_do_not_exist()
    problems += vendored_copy_drifted()
    for asset in sorted((BUILD / "assets").rglob("*")):
        if asset.suffix not in (".css", ".js") or "vendor" in asset.parts:
            continue
        for m in re.finditer(r"url\(\s*['\"]?(?:https?:)?//|(?:fetch|import)\s*\(?\s*['\"](?:https?:)?//|from\s+['\"](?:https?:)?//",
                             asset.read_text()):
            problems.append(f"{asset.relative_to(BUILD)}: loads from another site: {m.group(0)}")

    problems += names_that_must_not_appear(pages)
    problems += gate_blind_spots()

    print("-" * 52)
    if problems:
        print(f"{len(problems)} problems:")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"{len(pages)} pages, every link resolves, nothing unreleased is named")
    return 0


#: Patterns that give nothing away by being written down. The first holds
#: for the built pages only, whose links must stay inside the site.
PAGES_ONLY = [(r"\.\./\.\.", "a path outside the site")]
PUBLIC = [
    (r"(?i)[\w.+-]+@gmail\.com", "a personal address"),
    (r"(?i)/home/[a-z]", "a path on somebody's machine"),
]


def private_words() -> list[tuple[str, str, str]]:
    """What nothing published may name: unreleased devices and projects,
    part numbers, register names, people, private repositories.

    These are themselves what they protect, so they are not written here:
    they live on the maintainers' machines, in the file
    INTOMIND_PRIVATE_WORDS names or ~/.config/intomind/private-words.tsv,
    one pattern per line, then what it is, "fold" or "exact", and an
    example the check must catch, separated by tabs. Without the file the
    check fails and says why: a check that quietly does not run is not a
    check. Returns (pattern with its case flag, what it is, example)."""
    path = pathlib.Path(os.environ.get("INTOMIND_PRIVATE_WORDS",
                                       "~/.config/intomind/private-words.tsv")).expanduser()
    if not path.is_file():
        raise SystemExit(f"the private word list is not on this machine ({path}), so what "
                         "this site may publish cannot be checked. Set INTOMIND_PRIVATE_WORDS to it.")
    out = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        pattern, why, case, example = line.split("\t")
        out.append(((("(?i)" if case == "fold" else "") + pattern), why, example))
    return out


#: The wire field is spelled this way in the contract every
#: implementation is held to, so it is our word and not a borrowed one.
#: Renaming it would change the contract and hide nothing: the gain
#: ladder and the converter width say as much to a reader who is looking.
#: Listed so the choice is deliberate rather than an oversight.
ALLOWED = [re.compile(r"loff_statp", re.I)]


def _hits(text: str, patterns) -> list[str]:
    out = []
    for pattern, why in patterns:
        for m in re.finditer(pattern, text):
            if any(a.fullmatch(m.group(0)) for a in ALLOWED):
                continue
            out.append(f"names {m.group(0)}, which is {why}")
    return sorted(set(out))


def names_that_must_not_appear(pages) -> list[str]:
    """Every banned name, in every built page and every tracked file.

    The built HTML is read because what is served is what matters and a
    page can be assembled from somewhere else (see `ASSEMBLED` in the
    build). The tracked files are read because the repository is
    published too: a path in the build script is as public as a page.
    """
    private = [(p, w) for p, w, _e in private_words()]
    problems: list[str] = []
    for f in pages:
        for hit in _hits(f.read_text(), PAGES_ONLY + PUBLIC + private):
            problems.append(f"{f.name}: {hit}")
    listed = subprocess.run(["git", "ls-files"], cwd=HERE, capture_output=True, text=True, check=True).stdout.split()
    for name in listed:
        try:
            text = (HERE / name).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        # This file writes the public patterns down, so it is held to the
        # private words alone, which it never writes.
        patterns = private if name == "check.py" else PUBLIC + private
        for hit in _hits(text, patterns):
            problems.append(f"{name}: {hit}")
    return problems


def vendored_copy_drifted() -> list[str]:
    """The site's copy of the SDK, byte for byte the published one."""
    problems = []
    found = {str(p.relative_to(VENDORED)) for p in VENDORED.rglob("*.js")}
    if found != set(VENDORED_SHA256):
        problems.append(f"the vendored SDK holds {sorted(found)}, not {sorted(VENDORED_SHA256)}")
    for name, want in VENDORED_SHA256.items():
        path = VENDORED / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != want:
            problems.append(f"the vendored SDK's {name} is not the published file")
    return problems


def gate_blind_spots() -> list[str]:
    """A gate never seen to fail is not a gate: every private pattern must
    catch its own example."""
    problems = []
    for pattern, why, example in private_words():
        if not re.search(pattern, example):
            problems.append(f"the pattern for {why} does not catch its own example {example!r}")
    return problems


def names_that_do_not_exist() -> list[str]:
    """Every dotted name a Python example shows, resolved for real.

    An example is a promise. A name that moved, or a keyword argument that
    became positional, costs a reader their first hour and costs us their
    trust, and neither shows up in a link check.
    """
    problems: list[str] = []
    try:
        import intomind  # noqa: F401
    except ImportError:
        return ["the instrument library is not installed, so no example was checked"]

    import importlib

    checked = 0
    for page in sorted((HERE / "pages").glob("*.md")):
        text = page.read_text()
        for block in re.findall(r"```python\n(.*?)```", text, re.S):
            for module, rest in re.findall(
                    r"\b(intomind(?:\.\w+)*)\b(?:\s+import\s+([\w, ]+))?", block):
                try:
                    m = importlib.import_module(module)
                except Exception as e:
                    problems.append(f"{page.name}: {module} does not import ({e})")
                    continue
                checked += 1
                for name in (rest or "").replace(" ", "").split(","):
                    if name and not hasattr(m, name):
                        problems.append(f"{page.name}: {module} has no {name}")
                    elif name:
                        checked += 1
            # Attribute chains off a module this page imported.
            for owner, attr in re.findall(r"\b(\w+)\.(\w+)\(", block):
                mod = f"intomind.{owner}"
                if f"import {owner}" not in block and f"from intomind import" not in block:
                    continue
                try:
                    m = importlib.import_module(mod)
                except Exception:
                    continue
                if not hasattr(m, attr):
                    problems.append(f"{page.name}: {mod} has no {attr}()")
                else:
                    checked += 1
    if not checked:
        problems.append("no example name was checked, so this gate proves nothing")
    return problems


if __name__ == "__main__":
    sys.exit(main())
