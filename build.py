"""Turn the Markdown in pages/ into the site in build/.

No dependencies, on purpose. Every layer between the text and the page is
a layer that can stop working, and this has to be buildable in ten years.

Some pages are assembled from the documents they publish, so that a
released version and its documentation cannot disagree about what the
software does. Those pages say where they came from.

Besides the pages, the build writes what search engines and AI assistants
read: each page again as plain Markdown, `llms.txt` and `llms-full.txt`, a
sitemap, structured data in every page, and an index for the site's own
search box.
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAGES = HERE / "pages"
ASSETS = HERE / "assets"
BUILD = HERE / "build"

SITE_URL = "https://docs.intomind.com"
COMPANY_URL = "https://www.intomind.com"
SOCIAL_IMAGE = "https://www.intomind.com/logo/1200x630.png"

#: Where the protocol's documents are read from: the folder
#: INTOMIND_PROTOCOL_DIR names, or ~/.config/intomind/protocol, where the
#: maintainers keep them. Nobody's directory layout is written here.
PROTOCOL_DIR = pathlib.Path(os.environ.get("INTOMIND_PROTOCOL_DIR", "~/.config/intomind/protocol")).expanduser()

#: Pages assembled from elsewhere. Each is (destination, source, credit,
#: description). The source is a file in PROTOCOL_DIR; the credit is what
#: the page says about where it came from. A missing source is reported
#: rather than silently skipped, because a page that quietly stops being
#: generated is a page that goes stale.
ASSEMBLED = [
    ("protocol.md", "intomind-ble-protocol-v1.4.md",
     "the protocol contract the firmware and every host implement",
     "Version 1.4 of the IntoMind Bluetooth protocol: USB power, the heads' encoder ids, "
     "and embedding notifications that fit every link."),
    ("protocol-1-3.md", "intomind-ble-protocol-v1.3.md",
     "version 1.3 of the protocol contract",
     "Version 1.3 of the IntoMind Bluetooth protocol: model cadence, the synthetic signal, "
     "weights updates, and the device's name."),
    ("protocol-1-2.md", "intomind-ble-protocol-v1.2.md",
     "version 1.2 of the protocol contract",
     "Version 1.2 of the IntoMind Bluetooth protocol: the status light, the converter's "
     "registers, and embeddings."),
    ("protocol-1-1.md", "intomind-ble-protocol-v1.1.md",
     "version 1.1 of the protocol contract",
     "Version 1.1 of the IntoMind Bluetooth protocol, the whole contract as it stood then: "
     "services, packets, commands, updates, heads, and processing on the device."),
    ("protocol-1-0.md", "intomind-ble-protocol-v1.0.md",
     "version 1.0 of the protocol contract",
     "Version 1.0 of the IntoMind Bluetooth protocol, the first frozen contract."),
]

#: The contract grows by addition, one document per version, newest first.
VERSIONS = [("protocol.html", "1.4"), ("protocol-1-3.html", "1.3"),
            ("protocol-1-2.html", "1.2"), ("protocol-1-1.html", "1.1"),
            ("protocol-1-0.html", "1.0")]

#: The navigation, in order.
NAV = [
    ("index.html", "Start"),
    ("device.html", "The device"),
    ("command-center.html", "Command Center"),
    ("python.html", "Python"),
    ("rust.html", "Rust"),
    ("javascript.html", "JavaScript"),
    ("micropython.html", "MicroPython"),
    ("model.html", "The model and heads"),
    ("protocol.html", "The protocol"),
    ("safety.html", "Safety and care"),
    ("glossary.html", "Glossary"),
]

#: Interactive parts a page asks for with a line of its own, `{{name}}`.
#: Each is the HTML that stands in its place and the script that brings
#: it to life. The Markdown twin of a page drops the line: the text around
#: every one of them says what it shows.
WIDGETS = {
    "light-patterns": ('<div class="widget" data-widget="light-patterns"></div>', "widgets/light.js"),
    "name-composer": ('<div class="widget" data-widget="name-composer"></div>', "widgets/name.js"),
    "packet-decoder": ('<div class="widget" data-widget="packet-decoder"></div>', "widgets/decoder.js"),
    "live-demo": ('<div class="widget" data-widget="live-demo"></div>', "widgets/live.js"),
}

KEYWORDS = {
    "python": "False None True and as assert async await break class continue def del elif else except "
              "finally for from global if import in is lambda nonlocal not or pass raise return try while with yield",
    "rust": "as async await break const continue crate dyn else enum extern false fn for if impl in let loop match "
            "mod move mut pub ref return self Self static struct super trait true type unsafe use where while",
    "javascript": "async await break case catch class const continue default delete do else export extends false "
                  "finally for from function if import in instanceof let new null of return static super switch "
                  "this throw true try typeof undefined var void while yield",
}
for alias in ("js", "ts", "typescript"):
    KEYWORDS[alias] = KEYWORDS["javascript"]

LANGUAGE_LABELS = {"python": "Python", "micropython": "MicroPython", "rust": "Rust", "javascript": "JavaScript", "js": "JavaScript",
                   "ts": "TypeScript", "typescript": "TypeScript", "sh": "Terminal", "shell": "Terminal",
                   "bash": "Terminal", "json": "JSON", "html": "HTML", "toml": "TOML"}


# The Markdown this site uses, and no more.

def slug(text: str) -> str:
    text = re.sub(r"<[^>]+>|`", "", text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-") or "section"


def inline(text: str) -> str:
    """The small marks, after escaping. Order matters: code first, so a
    backtick span is never reinterpreted."""
    out, at = [], 0
    for m in re.finditer(r"`([^`]+)`", text):
        out.append(emphasis(html.escape(text[at:m.start()], quote=False)))
        out.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        at = m.end()
    out.append(emphasis(html.escape(text[at:], quote=False)))
    # A steady light drawn in the text, kept on one line with the word after
    # it, where a light is described: {{lamp}} Power.
    text = "".join(out).replace("™", '<sup class="tm">™</sup>')
    return re.sub(r"\{\{lamp\}\} (\S+)",
                  r'<span class="lit"><span class="lamp-inline" aria-hidden="true"></span>\1</span>', text)


def emphasis(text: str) -> str:
    def link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        external = href.startswith(("http://", "https://")) and not href.startswith(SITE_URL)
        return f'<a href="{href}"' + (' rel="noopener"' if external else "") + f">{label}</a>"

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<em>\1</em>", text)


def highlight(code: str, lang: str) -> str:
    """Color a code block at build time, so the page needs no script for
    it: comments, strings, numbers, keywords, types, and called names.
    Nothing cleverer, because a highlighter that guesses wrong misleads."""
    lang = lang.lower()
    if lang == "micropython":
        lang = "python"  # the same language, to a highlighter
    if lang in ("sh", "shell", "bash", "console"):
        return re.sub(r"^(\s*)(#.*)$", r'\1<span class="c">\2</span>', html.escape(code, quote=False), flags=re.M)
    if lang not in KEYWORDS:
        return html.escape(code, quote=False)
    words = set(KEYWORDS[lang].split())
    if lang == "python":
        comment = r"#[^\n]*"
        string = r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|[rbf]?"(?:\\.|[^"\\\n])*"|[rbf]?\'(?:\\.|[^\'\\\n])*\''
    elif lang == "rust":
        comment = r"//[^\n]*|/\*[\s\S]*?\*/"
        string = r'b?"(?:\\.|[^"\\])*"|b?\'(?:\\.|[^\'\\\n])\''
    else:
        comment = r"//[^\n]*|/\*[\s\S]*?\*/"
        string = r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`'
    token = re.compile(rf"(?P<c>{comment})|(?P<s>{string})"
                       r"|(?P<n>\b0x[0-9a-fA-F_]+\b|\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?n?\b)"
                       r"|(?P<w>[A-Za-z_][A-Za-z0-9_]*!?)")
    out, at = [], 0
    for m in token.finditer(code):
        out.append(html.escape(code[at:m.start()], quote=False))
        text = html.escape(m.group(0), quote=False)
        word = m.group("w")
        if m.group("c"):
            out.append(f'<span class="c">{text}</span>')
        elif m.group("s"):
            out.append(f'<span class="s">{text}</span>')
        elif m.group("n"):
            out.append(f'<span class="n">{text}</span>')
        elif word in words:
            out.append(f'<span class="k">{text}</span>')
        elif code[m.end():m.end() + 1] == "(" or word.endswith("!"):
            out.append(f'<span class="f">{text}</span>')
        elif word[:1].isupper() and not word.isupper():
            out.append(f'<span class="t">{text}</span>')
        else:
            out.append(text)
        at = m.end()
    out.append(html.escape(code[at:], quote=False))
    return "".join(out)


class Rendered:
    """A page's body as HTML, the headings it holds for the table of
    contents, and the widgets it asks for."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.toc: list[tuple[int, str, str]] = []
        self.widgets: list[str] = []
        self.ids: set[str] = set()

    def heading(self, level: int, text: str) -> str:
        if level == 1:
            return f"<h1>{inline(text)}</h1>"
        base = slug(text)
        ident, n = base, 2
        while ident in self.ids:
            ident, n = f"{base}-{n}", n + 1
        self.ids.add(ident)
        if level in (2, 3):
            self.toc.append((level, ident, re.sub(r"<[^>]+>", "", inline(text))))
        return f'<h{level} id="{ident}">{inline(text)}</h{level}>'


def cards(block: list[str]) -> str:
    """A ```cards block: one line per card, `title | page | what it covers`."""
    items = []
    for line in block:
        title, href, text = (part.strip() for part in line.split("|", 2))
        items.append(f'<li><a href="{href}"><b>{inline(title)}</b><span>{inline(text)}</span></a></li>')
    return '<ul class="paths">' + "".join(items) + "</ul>"


def cards_as_text(md: str) -> str:
    """The same cards for a reader of the Markdown: a list of links."""
    def one(m: re.Match) -> str:
        lines = []
        for line in m.group(1).strip().splitlines():
            title, href, text = (part.strip() for part in line.split("|", 2))
            url = SITE_URL + "/" + href.lstrip("/").replace(".html", ".md")
            lines.append(f"- [{title}]({url}): {text}")
        return "\n".join(lines)
    return re.sub(r"^```cards\n(.*?)^```\n?", one, md, flags=re.M | re.S)


def render(md: str, lead: bool = True) -> Rendered:
    """Markdown, as much of it as this site uses and no more. With `lead`,
    the first paragraph after the title is set as the page's lead."""
    r = Rendered()
    out = r.parts
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if m := re.fullmatch(r"\{\{([a-z-]+)\}\}", line.strip()):
            if m.group(1) not in WIDGETS:
                raise SystemExit(f"a page asks for a widget that does not exist: {m.group(1)}")
            out.append(WIDGETS[m.group(1)][0])
            r.widgets.append(m.group(1))
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if lang == "cards":
                out.append(cards(block))
                continue
            label = LANGUAGE_LABELS.get(lang.lower())
            out.append("<pre" + (f' data-lang="{label}"' if label else "") + f'><code class="language-{html.escape(lang or "text")}">'
                       + highlight("\n".join(block), lang) + "</code></pre>")
            continue
        if line.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            table = ['<div class="table"><table>']
            if any(head):
                table.append("<thead><tr>" + "".join(f'<th scope="col">{inline(c)}</th>' for c in head) + "</tr></thead>")
            table.append("<tbody>")
            for row in rows:
                table.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
            table.append("</tbody></table></div>")
            out.append("".join(table))
            continue
        if m := re.match(r"(#{1,4}) +(.*)", line):
            out.append(r.heading(len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i][1:].strip())
                i += 1
            text = " ".join(block)
            kind = "note"
            if m := re.match(r"\*\*(Note|Important|Warning)\.?\*\*", text):
                kind = m.group(1).lower()
                if kind == "warning":
                    # A warning says what to do in its first words; its color marks it.
                    text = text[m.end():].strip()
            out.append(f'<aside class="callout {kind}" role="note" aria-label="{kind.title()}"><p>{inline(text)}</p></aside>')
            continue
        if re.match(r"[-*] +", line) or re.match(r"\d+\. +", line):
            ordered = bool(re.match(r"\d+\. ", line))
            tag = "ol" if ordered else "ul"
            items = []  # [text, nested list html]
            while i < len(lines) and (re.match(r"[-*] +", lines[i]) or re.match(r"\d+\. +", lines[i])):
                items.append([re.sub(r"^(?:[-*]|\d+\.) +", "", lines[i]), ""])
                i += 1
                # An item wrapped in the source continues on indented lines
                # until the next item or a blank line. An indented bullet
                # starts a list nested one level in, whose own items may
                # wrap onto lines indented further still.
                while i < len(lines) and lines[i].strip() and lines[i][0] in " \t":
                    if re.match(r"\s+(?:[-*]|\d+\.) +", lines[i]):
                        sub_tag = "ol" if re.match(r"\s+\d+\. ", lines[i]) else "ul"
                        indent = len(lines[i]) - len(lines[i].lstrip())
                        sub = []
                        while (i < len(lines) and re.match(r"\s+(?:[-*]|\d+\.) +", lines[i])
                               and len(lines[i]) - len(lines[i].lstrip()) == indent):
                            sub.append(re.sub(r"^\s+(?:[-*]|\d+\.) +", "", lines[i]))
                            i += 1
                            while i < len(lines) and lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) > indent:
                                sub[-1] += " " + lines[i].strip()
                                i += 1
                        items[-1][1] += f"<{sub_tag}>" + "".join(f"<li>{inline(t)}</li>" for t in sub) + f"</{sub_tag}>"
                    else:
                        items[-1][0] += " " + lines[i].strip()
                        i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}{n}</li>" for t, n in items) + f"</{tag}>")
            continue
        if not line.strip():
            i += 1
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "```", ">", "- ", "* ", "{{")):
            para.append(lines[i])
            i += 1
        text = " ".join(para)
        if m := re.fullmatch(r"!\[([^\]]+)\]\(([^)\s]+)\)", text.strip()):
            alt, src = m.group(1), m.group(2)
            if src.startswith("/assets/img/") and src.endswith(".svg"):
                # A drawing of our own goes into the page itself, so it is
                # set in the page's typefaces and follows its light or dark.
                svg = (ASSETS / src[len("/assets/"):]).read_text()
                svg = svg.replace("<svg ", f'<svg role="img" aria-label="{html.escape(alt)}" ', 1)
                out.append(f"<figure>{svg}<figcaption>{inline(alt)}</figcaption></figure>")
            else:
                out.append(f'<figure><img src="{src}" alt="{html.escape(alt)}" loading="lazy">'
                           f"<figcaption>{inline(alt)}</figcaption></figure>")
        elif lead and out and out[-1].startswith("<h1>"):
            out.append(f'<p class="lead">{inline(text)}</p>')
        else:
            out.append(f"<p>{inline(text)}</p>")
    return r


# Pages.

def front_matter(text: str) -> tuple[dict[str, str], str]:
    """`title` and `description` from a block at the top of a page, and
    the rest of the page."""
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.index("\n---\n", 4)
        for line in text[4:end].splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        text = text[end + 5:].lstrip("\n")
    return meta, text


def plain(fragment: str) -> str:
    """The words of an HTML fragment, without its code blocks."""
    text = re.sub(r"<pre.*?</pre>", " ", fragment, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def nav_html(here: str) -> str:
    items = "".join(f'<li><a href="/{href}"{' aria-current="page"' if href == here else ""}>{html.escape(label)}</a></li>'
                    for href, label in NAV)
    return f'<nav class="sidebar" id="sidebar" aria-label="Pages"><ul>{items}</ul></nav>'


def toc_html(toc: list[tuple[int, str, str]]) -> str:
    if len(toc) < 3:
        return ""
    items = "".join(f'<li class="l{level}"><a href="#{ident}">{html.escape(text)}</a></li>' for level, ident, text in toc)
    return f'<aside class="toc" aria-label="On this page"><p>On this page</p><ul>{items}</ul></aside>'


def json_ld(name: str, title: str, description: str) -> str:
    """What a search engine reads about the page: who publishes it, what
    it is about, and where it sits in the site."""
    url = f"{SITE_URL}/" if name == "index.html" else f"{SITE_URL}/{name}"
    org = {"@type": "Organization", "name": "IntoMind, Inc.", "url": COMPANY_URL,
           "logo": f"{COMPANY_URL}/logo/180.png"}
    graph: list[dict] = []
    if name == "index.html":
        graph.append({"@type": "WebSite", "name": "IntoMind documentation", "url": f"{SITE_URL}/",
                      "publisher": org, "inLanguage": "en-US"})
    graph.append({"@type": "TechArticle", "headline": title, "description": description, "url": url,
                  "inLanguage": "en-US", "publisher": org,
                  "about": {"@type": "Product", "name": "IntoMind One", "model": "IM-1",
                            "brand": {"@type": "Brand", "name": "IntoMind"}}})
    if name != "index.html":
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "IntoMind documentation", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": url}]})
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    data = data.replace("</", "<\\/")
    return f'<script type="application/ld+json">{data}</script>'


def page(name: str, title: str, description: str, body: Rendered, source: str | None = None) -> str:
    note = ""
    if source:
        note = f'<p class="source">This page is {html.escape(source)}, so it cannot disagree with the software it describes.</p>'
    if any(href == name for href, _ in VERSIONS):
        links = ", ".join(v if href == name else f'<a href="/{href}">{v}</a>' for href, v in VERSIONS)
        note += (f'<p class="source">Each version adds to the one before it: {links}. Version 1.1 restates the whole '
                 'contract as it stood then.</p>')
    url = f"{SITE_URL}/" if name == "index.html" else f"{SITE_URL}/{name}"
    twin = "/" + name[:-5] + ".md"
    full_title = "IntoMind One documentation" if name == "index.html" else f"{title} | IntoMind documentation"
    scripts = "".join(f'<script type="module" src="/assets/{WIDGETS[w][1]}"></script>' for w in dict.fromkeys(body.widgets))
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">
<link rel="alternate" type="text/markdown" href="{twin}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="IntoMind documentation">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SOCIAL_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f2f2ee" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#222222" media="(prefers-color-scheme: dark)">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/icon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/icon-180.png">
<link rel="preload" href="/assets/fonts/Sen-variable.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="/assets/site.css">
{json_ld(name, title, description)}
</head>
<body>
<a class="skip" href="#content">Skip to the content</a>
<header class="top">
<button class="menu" type="button" aria-controls="sidebar" aria-expanded="false"><span></span>Pages</button>
<a class="mark" href="https://intomind.com">IntoMind<sup>&trade;</sup></a><a class="docs" href="/">Docs</a>
<div class="search" role="search"><input type="search" id="q" placeholder="Search" aria-label="Search the documentation" autocomplete="off" spellcheck="false"><kbd>/</kbd><ol id="results" hidden></ol></div>
</header>
<div class="frame">
{nav_html(name)}
<main id="content">
<article>
{note}{"".join(body.parts)}
</article>
</main>
{toc_html(body.toc)}
</div>
<footer><div>IntoMind is a trademark of IntoMind, Inc. Source code is at
<a href="https://github.com/intomind" rel="noopener">github.com/intomind</a>. IntoMind One is not a medical device.</div></footer>
<script src="/assets/site.js" defer></script>
{scripts}
</body>
</html>
"""


def last_changed(path: pathlib.Path) -> str | None:
    """The date of the last commit that changed a page's source, for the
    sitemap, or nothing when the history cannot be read."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path.name], cwd=path.parent,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return out or None


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    shutil.copytree(ASSETS, BUILD / "assets")

    missing = []
    sources: dict[str, pathlib.Path] = {}
    for dest, source, _credit, _description in ASSEMBLED:
        src = (PROTOCOL_DIR / source).resolve()
        if not src.exists():
            missing.append(f"{dest}: {src} is not there")
            continue
        (PAGES / dest).write_text(src.read_text())
        sources[dest] = src
        print(f"  assembled {dest} from {src}")

    built: dict[str, tuple[str, str, str]] = {}  # name: title, description, Markdown
    index: list[dict] = []
    for md in sorted(PAGES.glob("*.md")):
        name = md.stem + ".html"
        meta, text = front_matter(md.read_text())
        title = meta.get("title") or next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), md.stem)
        assembled = next(((c, d) for dst, _s, c, d in ASSEMBLED if dst == md.name), None)
        description = meta.get("description") or (assembled[1] if assembled else "")
        if not description:
            missing.append(f"{md.name} has no description")
        body = render(text, lead=assembled is None)
        if md.name == "protocol.md":
            # After the contract, untouched: a decoder for its sample packets.
            body.parts.append('<h2 id="decode-a-packet">Decode a packet</h2><p>Paste the bytes of an EEG Data '
                              'notification in hexadecimal, or try an example. The JavaScript SDK\'s decoder reads it.</p>'
                              + WIDGETS["packet-decoder"][0])
            body.widgets.append("packet-decoder")
            body.toc.append((2, "decode-a-packet", "Decode a packet"))
        (BUILD / name).write_text(page(name, title, description, body, assembled[0] if assembled else None))
        twin = cards_as_text(text)
        for w in WIDGETS:
            twin = re.sub(r"^" + re.escape("{{" + w + "}}") + r"\n\n?", "", twin, flags=re.M)
        # A reader of the Markdown may have it without the site around it.
        twin = re.sub(r"\]\(/", f"]({SITE_URL}/", twin)
        twin = twin.replace("{{lamp}} ", "")
        (BUILD / (md.stem + ".md")).write_text(f"---\ntitle: {title}\ndescription: {description}\n"
                                               f"url: {SITE_URL}/{name}\n---\n\n{twin.strip()}\n")
        built[name] = (title, description, twin)
        # One search entry per section, so a hit lands on its heading.
        for chunk in re.split(r'(?=<h[23] id=")', "".join(body.parts)):
            m = re.match(r'<h[23] id="([^"]+)">(.*?)</h[23]>', chunk)
            words = plain(chunk)
            if words:
                index.append({"u": f"/{name}" + (f"#{m.group(1)}" if m else ""), "t": title,
                              "s": plain(m.group(2)) if m else "", "x": words})

    nf = Rendered()
    nf.parts.append("<h1>Not found</h1><p>There is no page at this address. The pages are listed on the left, "
                    "and the search box above looks through all of them.</p>")
    (BUILD / "404.html").write_text(page("404.html", "Not found", "There is no page at this address on the IntoMind documentation site.", nf))

    order = [href for href, _l in NAV]
    ordered = sorted(built, key=lambda n: order.index(n) if n in order else len(order))

    # What AI assistants read: an index of the site, and all of it in one file.
    llms = ["# IntoMind One documentation", "",
            "> IntoMind One (model IM-1) is a four-channel wearable EEG device. It streams timestamped 24-bit "
            "signal to a computer over Bluetooth Low Energy, runs a small neural network on the device, and marks "
            "every lost sample. This site documents the device, the Command Center, the Python API, the JavaScript and "
            "Rust SDK, the model on the device, and the Bluetooth protocol.", "",
            "Every page is also published as Markdown, at the same address with `.md` in place of `.html`.", ""]
    for heading, names in [("Docs", [n for n in ordered if not n.startswith("protocol")]),
                           ("Protocol contract", [VERSIONS[0][0]]),
                           ("Optional", [href for href, _ in VERSIONS[1:]])]:
        llms += [f"## {heading}", ""]
        llms += [f"- [{built[n][0]}]({SITE_URL}/{n[:-5]}.md): {built[n][1]}" for n in names if n in built]
        llms.append("")
    (BUILD / "llms.txt").write_text("\n".join(llms))
    full = ["# IntoMind One documentation", ""]
    for n in ordered:
        if not n.startswith("protocol-1-") or n == VERSIONS[0][0]:
            full += [f"<!-- {SITE_URL}/{n} -->", "", built[n][2].strip(), ""]
    (BUILD / "llms-full.txt").write_text("\n".join(full))

    # What search engines read.
    urls = []
    for n in ordered:
        changed = last_changed(sources.get(n[:-5] + ".md") or PAGES / (n[:-5] + ".md"))
        loc = f"{SITE_URL}/" if n == "index.html" else f"{SITE_URL}/{n}"
        urls.append(f"  <url><loc>{loc}</loc>" + (f"<lastmod>{changed}</lastmod>" if changed else "") + "</url>")
    (BUILD / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "\n".join(urls) + "\n</urlset>\n")
    (BUILD / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    (BUILD / "search.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))

    for href, label in NAV:
        if not (BUILD / href).exists():
            missing.append(f"{href} is in the navigation and was not built ({label})")

    print(f"{len(built)} pages into {BUILD}")
    if missing:
        print("\nnot right yet:")
        for m in missing:
            print(f"  {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
