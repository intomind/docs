// docs.intomind.com: the page list on small screens, copy buttons, the
// contents highlight, and search. Nothing here is needed to read a page.
"use strict";

(() => {
  // The page list on small screens.
  const menu = document.querySelector(".menu");
  const sidebar = document.getElementById("sidebar");
  if (menu && sidebar) {
    menu.addEventListener("click", () => {
      const open = sidebar.classList.toggle("open");
      menu.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !menu.contains(e.target)) {
        sidebar.classList.remove("open");
        menu.setAttribute("aria-expanded", "false");
      }
    });
  }

  // A copy button on every code block.
  for (const pre of document.querySelectorAll("pre")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.textContent = "Copy";
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.querySelector("code").innerText);
        button.textContent = "Copied";
        button.classList.add("done");
      } catch {
        button.textContent = "Select and copy";
      }
      setTimeout(() => { button.textContent = "Copy"; button.classList.remove("done"); }, 1600);
    });
    pre.appendChild(button);
  }

  // The contents column follows the reader. A section is current once its
  // heading passes the top of the window. At the end of the page, where the
  // last sections cannot reach the top, the one chosen in the contents is
  // current, or else the last.
  const links = new Map([...document.querySelectorAll(".toc a")].map((a) => [a.hash.slice(1), a]));
  const heads = [...links.keys()].map((id) => document.getElementById(id)).filter(Boolean);
  if (heads.length) {
    let chosen = null;
    const mark = (id) => { for (const [key, a] of links) a.classList.toggle("here", key === id); };
    const follow = () => {
      if (chosen) {
        const top = document.getElementById(chosen).getBoundingClientRect().top;
        if (top >= 0 && top < window.innerHeight) return mark(chosen);
        chosen = null;
      }
      let current = heads[0].id;
      for (const h of heads) if (h.getBoundingClientRect().top <= 110) current = h.id;
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = heads[heads.length - 1].id;
      mark(current);
    };
    for (const [id, a] of links) a.addEventListener("click", () => { chosen = id; mark(id); });
    // Scrolling by hand lets the position decide again.
    for (const kind of ["wheel", "touchmove", "keydown"]) window.addEventListener(kind, () => { if (chosen) { chosen = null; follow(); } }, { passive: true });
    window.addEventListener("scroll", follow, { passive: true });
    follow();
  }

  // Search, over an index the build writes. It is fetched the first time
  // the box is used, and nothing leaves the page.
  const input = document.getElementById("q");
  const list = document.getElementById("results");
  if (!input || !list) return;
  let index = null;
  let picked = -1;

  const load = async () => {
    if (index) return index;
    const r = await fetch("/search.json");
    index = (await r.json()).map((e) => ({ ...e, lt: e.t.toLowerCase(), ls: e.s.toLowerCase(), lx: e.x.toLowerCase() }));
    return index;
  };

  const escape = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // The words around the first match, with every term marked.
  const excerpt = (text, terms) => {
    const lower = text.toLowerCase();
    const at = Math.max(0, Math.min(...terms.map((t) => lower.indexOf(t)).filter((i) => i >= 0)) - 60);
    let s = (at > 0 ? "…" : "") + text.slice(at, at + 170) + (at + 170 < text.length ? "…" : "");
    s = escape(s);
    for (const t of terms) s = s.replace(new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), (m) => `<mark>${m}</mark>`);
    return s;
  };

  const show = async () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { list.hidden = true; return; }
    const terms = q.split(/\s+/).filter(Boolean);
    const entries = await load();
    const scored = [];
    for (const e of entries) {
      if (!terms.every((t) => e.lt.includes(t) || e.ls.includes(t) || e.lx.includes(t))) continue;
      let score = 0;
      for (const t of terms) {
        if (e.ls.includes(t)) score += 6;
        if (e.lt.includes(t)) score += 4;
        score += Math.min(3, e.lx.split(t).length - 1);
      }
      if (e.ls.includes(q)) score += 8;
      scored.push([score, e]);
    }
    scored.sort((a, b) => b[0] - a[0]);
    picked = -1;
    list.innerHTML = scored.length
      ? scored.slice(0, 8).map(([, e]) => `<li><a href="${e.u}"><b>${escape(e.s || e.t)}</b><small>${escape(e.s ? e.t : "")}${e.s ? " · " : ""}${excerpt(e.x, terms)}</small></a></li>`).join("")
      : '<li class="none">Nothing on this site matches that.</li>';
    list.hidden = false;
  };

  const move = (step) => {
    const items = [...list.querySelectorAll("li a")];
    if (!items.length) return;
    picked = (picked + step + items.length) % items.length;
    items.forEach((a, i) => a.parentElement.setAttribute("aria-selected", String(i === picked)));
    items[picked].scrollIntoView({ block: "nearest" });
  };

  input.addEventListener("input", show);
  input.addEventListener("focus", () => { load(); if (input.value) show(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") {
      const a = list.querySelectorAll("li a")[picked < 0 ? 0 : picked];
      if (a) location.href = a.href;
    } else if (e.key === "Escape") { list.hidden = true; input.blur(); }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) list.hidden = true; });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
      e.preventDefault();
      input.focus();
    }
  });
})();
