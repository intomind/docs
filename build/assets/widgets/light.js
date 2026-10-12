// The status light's patterns, played at the firmware's own timings, with
// the three settings that decide which of them show.
"use strict";

// Each pattern is its on and off times in milliseconds, repeated. A single
// time means always on.
// In order of priority: when two are true, the light shows the earlier.
const PATTERNS = [
  { name: "Identify", when: ["silent", "reserved", "verbose"], steps: [800, 200],
    note: "lit, with a short dark wink once a second" },
  { name: "Start-up check failed", when: ["reserved", "verbose"], steps: [80, 160, 80, 160, 80, 1200],
    note: "three blinks, then a pause" },
  { name: "Low battery", when: ["reserved", "verbose"], steps: [80, 160, 80, 1500],
    note: "two blinks, then a pause" },
  { name: "Update in progress", when: ["verbose"], steps: [100, 100], note: "fast blinking" },
  { name: "Streaming", when: ["verbose"], steps: [60, 1940], note: "a brief pulse every two seconds" },
  { name: "Connected", when: ["verbose"], steps: [1], note: "steady" },
  { name: "Waiting for a computer", when: ["verbose"], steps: [100, 900], note: "a short blink once a second" },
];

for (const root of document.querySelectorAll('[data-widget="light-patterns"]')) {
  root.innerHTML = `
    <h4>The status light, as the device shows it</h4>
    <div class="row" role="radiogroup" aria-label="Light setting" style="margin-bottom:0.9rem">
      ${["silent", "reserved", "verbose"].map((l) =>
        `<button type="button" class="quiet" role="radio" data-level="${l}">${l[0].toUpperCase() + l.slice(1)}</button>`).join("")}
    </div>
    <div class="lights">
      ${PATTERNS.map((p, i) => `
        <div class="light" data-i="${i}">
          <span class="lamp" aria-hidden="true"></span>
          <span><b>${p.name}</b><small>${p.note}</small></span>
        </div>`).join("")}
    </div>
    <p class="status" aria-live="polite"></p>`;

  // A pattern the chosen setting does not show stays dark, as on the device.
  let level = "reserved";
  const lamps = [...root.querySelectorAll(".light")];
  lamps.forEach((card, i) => {
    const lamp = card.querySelector(".lamp");
    const steps = PATTERNS[i].steps;
    let at = 0;
    const tick = () => {
      const shown = PATTERNS[i].when.includes(level);
      lamp.classList.toggle("on", shown && (steps.length === 1 || at % 2 === 0));
      const wait = steps.length === 1 ? 200 : steps[at];
      at = (at + 1) % steps.length;
      setTimeout(tick, wait);
    };
    tick();
  });

  const status = root.querySelector(".status");
  const choose = (chosen) => {
    level = chosen;
    for (const b of root.querySelectorAll("[data-level]")) {
      const on = b.dataset.level === level;
      b.setAttribute("aria-checked", String(on));
      b.classList.toggle("quiet", !on);
    }
    lamps.forEach((card, i) => card.classList.toggle("hidden-here", !PATTERNS[i].when.includes(level)));
    status.textContent = {
      silent: "Silent: the light stays dark, except when your software asks the device to identify itself.",
      reserved: "Reserved, the setting the device ships with: identify, a failed start-up check, and low battery.",
      verbose: "Verbose: everything. When several are true at once, the light shows the one highest in this list.",
    }[level];
  };
  for (const b of root.querySelectorAll("[data-level]")) b.addEventListener("click", () => choose(b.dataset.level));
  choose("reserved");
}
