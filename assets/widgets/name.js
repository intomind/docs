// The device's name, composed as the device composes it and counted as the
// device counts it, by the published SDK's own functions.
import * as P from "/assets/vendor/intomind-sdk-1.4.2/protocol.js";

const bytes = (s) => new TextEncoder().encode(s).length;

for (const root of document.querySelectorAll('[data-widget="name-composer"]')) {
  root.innerHTML = `
    <h4>Try a name</h4>
    <div class="row">
      <div><label for="nm-name">Name</label><input type="text" id="nm-name" value="Ada" maxlength="40"></div>
      <div><label for="nm-adj">Adjective</label><input type="text" id="nm-adj" value="Blue" maxlength="40"></div>
    </div>
    <p class="out" style="font-size:1.05rem;margin:0.9rem 0 0"></p>
    <div class="meter"><i></i></div>
    <p class="status" aria-live="polite"></p>`;
  const [name, adj] = root.querySelectorAll("input");
  const out = root.querySelector(".out");
  const meter = root.querySelector(".meter");
  const status = root.querySelector(".status");
  const update = () => {
    const n = name.value;
    const a = adj.value;
    const composed = P.composeName(n, a);
    const used = bytes(composed);
    out.textContent = composed;
    meter.querySelector("i").style.width = `${Math.min(100, (used / P.NAME_MAX_COMPOSED) * 100)}%`;
    meter.classList.toggle("over", used > P.NAME_MAX_COMPOSED);
    let why = "";
    if (used > P.NAME_MAX_COMPOSED) why = `That is ${used - P.NAME_MAX_COMPOSED} bytes too long. The device would refuse it.`;
    else if (!P.namePartOk(n) || !P.namePartOk(a)) why = "Neither part may start or end with a space or hold a control character.";
    const fits = P.nameFits(n, a);
    status.innerHTML = `${used} of ${P.NAME_MAX_COMPOSED} bytes. ` +
      (fits ? '<span class="good">The device accepts this name.</span>' : `<span class="bad">${why}</span>`);
  };
  name.addEventListener("input", update);
  adj.addEventListener("input", update);
  update();
}
