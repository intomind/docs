// An IntoMind One, live in this page over Web Bluetooth, through the
// published JavaScript SDK. Nothing is recorded and nothing leaves the
// browser: the samples are drawn and then dropped.
import { requestAndConnect } from "/assets/vendor/intomind-sdk-1.4.0/index.js";

const SECONDS = 5;
const COLORS = ["#ee2b7b", "#f7931a", "#4caf50", "#2f80ed"];

for (const root of document.querySelectorAll('[data-widget="live-demo"]')) {
  root.innerHTML = `
    <h4>Your IntoMind One, in this page</h4>
    <div class="row">
      <button type="button" data-do="connect">Connect</button>
      <button type="button" class="quiet" data-do="start" disabled>Start</button>
      <button type="button" class="quiet" data-do="stop" disabled>Stop</button>
      <button type="button" class="quiet" data-do="disconnect" disabled>Disconnect</button>
      <select aria-label="Vertical scale"><option value="50">±50 µV</option><option value="100" selected>±100 µV</option><option value="200">±200 µV</option><option value="1000">±1000 µV</option></select>
    </div>
    <canvas class="scope" style="margin-top:0.9rem"></canvas>
    <p class="status" aria-live="polite"></p>
    <dl class="fields"></dl>`;

  const button = (what) => root.querySelector(`[data-do="${what}"]`);
  const status = root.querySelector(".status");
  const fields = root.querySelector(".fields");
  const canvas = root.querySelector("canvas");
  const scale = root.querySelector("select");
  let link = null;
  let rate = 500;
  let lanes = [];
  let lost = 0;
  let received = 0;
  let battery = null;

  const say = (text) => { status.textContent = text; };
  const facts = () => {
    if (!link) { fields.innerHTML = ""; return; }
    const f = link.info.firmware.join(".");
    fields.innerHTML = `
      <dt>Device</dt><dd>${link.device.name ?? "IntoMind One"}</dd>
      <dt>Firmware</dt><dd>${f}</dd>
      <dt>Channels</dt><dd>${link.info.channels}, ${link.info.adcBits} bits</dd>
      <dt>Battery</dt><dd>${battery ?? "not reported yet"}</dd>
      <dt>Samples</dt><dd>${received} received, ${lost} lost and marked</dd>`;
  };
  const enable = (connected, streaming) => {
    button("connect").disabled = connected;
    button("disconnect").disabled = !connected;
    button("start").disabled = !connected || streaming;
    button("stop").disabled = !connected || !streaming;
  };

  if (!("bluetooth" in navigator)) {
    button("connect").disabled = true;
    say("This browser has no Web Bluetooth. Chrome has it on Windows, macOS, ChromeOS and Android, and Edge and Opera on Windows and macOS. On Linux, Chrome has it once chrome://flags/#enable-web-bluetooth is turned on. Safari and Firefox do not have it.");
  } else {
    say("Turn the device on, take it off the charger, and press Connect. Your browser lists the IntoMind devices nearby.");
  }

  const draw = () => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (canvas.width !== w * devicePixelRatio) { canvas.width = w * devicePixelRatio; canvas.height = h * devicePixelRatio; }
    const g = canvas.getContext("2d");
    g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    g.clearRect(0, 0, w, h);
    const span = Number(scale.value);
    const n = Math.max(1, lanes.length);
    const laneH = h / n;
    const width = rate * SECONDS;
    lanes.forEach((lane, c) => {
      const mid = laneH * (c + 0.5);
      g.strokeStyle = "rgba(255,255,255,0.08)";
      g.beginPath(); g.moveTo(0, mid); g.lineTo(w, mid); g.stroke();
      g.fillStyle = "rgba(241,236,228,0.6)";
      g.font = "11px system-ui, sans-serif";
      g.fillText(`Channel ${c + 1}`, 8, mid - laneH / 2 + 14);
      g.strokeStyle = COLORS[c % COLORS.length];
      g.lineWidth = 1.2;
      g.beginPath();
      let pen = false;
      const start = Math.max(0, lane.length - width);
      for (let i = start; i < lane.length; i++) {
        const v = lane[i];
        if (Number.isNaN(v)) { pen = false; continue; }
        const x = ((i - start) / width) * w;
        const y = mid - (Math.max(-span, Math.min(span, v)) / span) * (laneH / 2 - 4);
        pen ? g.lineTo(x, y) : g.moveTo(x, y);
        pen = true;
      }
      g.stroke();
    });
    if (link) requestAnimationFrame(draw);
  };

  const trim = () => { for (const lane of lanes) if (lane.length > rate * SECONDS * 2) lane.splice(0, lane.length - rate * SECONDS); };

  button("connect").addEventListener("click", async () => {
    try {
      say("Connecting. The first time, your computer pairs with the device.");
      link = await requestAndConnect({
        onDisconnect: () => { link = null; enable(false, false); say("The device disconnected."); facts(); },
      });
      lanes = Array.from({ length: link.info.channels }, () => []);
      link.on((event) => {
        if (event.type === "samples") {
          const b = event.batch;
          if (b.sampleRateHz) rate = b.sampleRateHz;
          for (let r = 0; r < b.rows; r++) for (let c = 0; c < b.channels; c++) lanes[c].push(b.microvolts(r, c, link.info));
          received += b.rows;
          trim();
        } else if (event.type === "gap") {
          for (const lane of lanes) lane.push(NaN);
          if (event.gap.samplesLost !== null) lost += event.gap.samplesLost;
        } else if (event.type === "status") {
          const s = event.status;
          battery = s.batteryPercent === null ? "not reported" : `${s.batteryPercent} percent${s.usbPresent ? ", on USB power" : ""}`;
        }
        facts();
      });
      enable(true, false);
      say("Connected. Press Start to see the signal.");
      facts();
      requestAnimationFrame(draw);
    } catch (e) {
      link = null;
      say(e.name === "NotFoundError" ? "No device was chosen." : `Not connected: ${e.message}`);
    }
  });

  button("start").addEventListener("click", async () => {
    const answer = await link.request(link.session.startStream());
    if (answer.ok) { enable(true, true); say("Streaming. The scale is fixed; change it on the right."); return; }
    say(answer.status === 7
      ? "The device does not stream from its electrodes while it is on USB power. Unplug it and press Start again."
      : `The device refused to start: ${answer.statusName}.`);
  });

  button("stop").addEventListener("click", async () => {
    await link.request(link.session.stopStream());
    enable(true, false);
    say("Stopped.");
  });

  button("disconnect").addEventListener("click", async () => {
    const l = link;
    link = null;
    await l.disconnect();
    enable(false, false);
    say("Disconnected.");
    facts();
  });
}
