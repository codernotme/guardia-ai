/**
 * Guardia AI v2.0.0 — Ground Control Station Tactical Frontend
 * Communicates with local FastAPI backend via WebSocket (/ws/telemetry)
 */

let ws = null;
let telemetry = {
  flight_mode: "STANDBY",
  armed: false,
  battery_v: 0.0,
  battery_pct: 100,
  gps_sats: 0,
  gps_fix: 0,
  alt: 0.0,
  groundspeed: 0.0,
  heading: 0.0,
  pitch: 0.0,
  roll: 0.0,
  target_locked: false,
  target_id: null,
};

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  logEntry("INFO", `Connecting to telemetry bridge: ${wsUrl}`);
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    logEntry("INFO", "Telemetry link established with Pixhawk 2.4.8 bridge");
    updatePill("hud-link-pill", "FC LINK ACTIVE", "hud-pill--connected");
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "TELEMETRY" && msg.data) {
        updateTelemetry(msg.data);
      } else if (msg.type === "DETECTION") {
        renderDetections(msg.data);
      } else if (msg.type === "ALERT") {
        logEntry("CRIT", `ALERT: ${msg.message}`);
      }
    } catch (e) {
      console.error("Telemetry parse error", e);
    }
  };

  ws.onclose = () => {
    updatePill("hud-link-pill", "FC LINK LOST", "hud-pill--danger");
    logEntry("WARN", "Telemetry link dropped. Reconnecting in 2s...");
    setTimeout(connectWebSocket, 2000);
  };
}

function updateTelemetry(data) {
  telemetry = { ...telemetry, ...data };

  // Update header indicators
  document.getElementById("val-flight-mode").innerText = telemetry.flight_mode;
  document.getElementById("val-alt").innerText = `${telemetry.alt.toFixed(1)}m`;
  document.getElementById("val-speed").innerText = `${telemetry.groundspeed.toFixed(1)}m/s`;
  document.getElementById("val-battery").innerText = `${telemetry.battery_v.toFixed(1)}V (${telemetry.battery_pct}%)`;
  document.getElementById("val-gps").innerText = `${telemetry.gps_sats} SATS (Fix ${telemetry.gps_fix})`;

  // Update arm status
  if (telemetry.armed) {
    updatePill("hud-arm-pill", "ARMED", "hud-pill--danger");
  } else {
    updatePill("hud-arm-pill", "DISARMED", "hud-pill--neutral");
  }

  // Update artificial horizon
  const horizonLadder = document.getElementById("hud-pitch-ladder");
  if (horizonLadder) {
    const pitchOffset = (telemetry.pitch || 0) * 80; // Scale pitch in pixels
    const rollAngle = (telemetry.roll || 0) * (180 / Math.PI);
    horizonLadder.style.transform = `translateY(${pitchOffset}px) rotate(${rollAngle}deg)`;
  }
}

function updatePill(id, text, className) {
  const el = document.getElementById(id);
  if (el) {
    el.innerText = text;
    el.className = `hud-pill ${className}`;
  }
}

function logEntry(level, text) {
  const stream = document.getElementById("hud-log-stream");
  if (!stream) return;

  const now = new Date().toTimeString().split(" ")[0];
  const li = document.createElement("li");
  li.className = `hud-log-entry ${level === "WARN" ? "hud-log-entry--warn" : level === "CRIT" ? "hud-log-entry--crit" : ""}`;
  li.innerHTML = `<span class="hud-log-time">[${now}]</span> <span>${text}</span>`;
  stream.prepend(li);

  while (stream.children.length > 25) {
    stream.removeChild(stream.lastChild);
  }
}

function sendCommand(command, params = {}, confirm = false) {
  logEntry("INFO", `Command dispatched: ${command.toUpperCase()}`);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ command, params, confirm }));
  } else {
    // Fallback to HTTP POST
    fetch("/api/v1/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, params, confirm }),
    })
      .then((res) => res.json())
      .then((data) => logEntry(data.ok ? "INFO" : "WARN", data.msg))
      .catch((err) => logEntry("CRIT", `Command failed: ${err}`));
  }
}

function renderDetections(detections) {
  const container = document.getElementById("hud-reticle-layer");
  if (!container) return;
  container.innerHTML = "";

  if (!detections || !detections.length) return;

  detections.forEach((det) => {
    const box = document.createElement("div");
    box.className = "hud-target-reticle";
    box.style.left = `${(det.bbox_x || 0.3) * 100}%`;
    box.style.top = `${(det.bbox_y || 0.3) * 100}%`;
    box.style.width = `${(det.bbox_w || 0.2) * 100}%`;
    box.style.height = `${(det.bbox_h || 0.3) * 100}%`;

    const tag = document.createElement("div");
    tag.className = "hud-reticle-tag";
    tag.innerText = `TRK-${det.track_id || 1} [${(det.class_name || "PERSON").toUpperCase()} ${Math.round((det.confidence || 0.9) * 100)}%]`;
    box.appendChild(tag);

    container.appendChild(box);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  connectWebSocket();

  // Button actions
  document.getElementById("btn-arm")?.addEventListener("click", () => sendCommand("arm"));
  document.getElementById("btn-takeoff")?.addEventListener("click", () => sendCommand("takeoff", { altitude: 10.0 }));
  document.getElementById("btn-hold")?.addEventListener("click", () => sendCommand("hold"));
  document.getElementById("btn-follow")?.addEventListener("click", () => sendCommand("follow_target", { class_name: "person" }));
  document.getElementById("btn-deliver")?.addEventListener("click", () => {
    if (confirm("Confirm Emergency Payload Release on Pixhawk AUX1?")) {
      sendCommand("deliver", {}, true);
    }
  });
  document.getElementById("btn-rtl")?.addEventListener("click", () => sendCommand("rtl"));
  document.getElementById("btn-kill")?.addEventListener("click", () => {
    if (confirm("⚠️ EMERGENCY MOTOR KILL: MOTORS WILL STOP IMMEDIATELY IN FLIGHT. PROCEED?")) {
      sendCommand("kill", {}, true);
    }
  });
});
