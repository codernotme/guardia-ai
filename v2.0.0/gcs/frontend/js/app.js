/**
 * Guardia AI v2.0.0 — Ground Control Station Tactical Frontend
 * Communicates with local FastAPI backend via WebSocket (/ws/telemetry)
 * Supports Step & Nudge Control (1cm, 10cm, 1ft, 1m) and FlySky RC Handover
 */

let ws = null;
let activeStepSize = 0.3048; // Default 1 ft (0.3048m)

let telemetry = {
  flight_mode: "STABILIZE",
  armed: false,
  battery_v: 0.0,
  battery_pct: 0,
  gps_sats: 0,
  gps_fix: 0,
  alt: 0.0,
  groundspeed: 0.0,
  heading: 0.0,
  pitch: 0.0,
  roll: 0.0,
  yaw: 0.0,
  rc_channels: [1500, 1500, 1100, 1500, 1000, 1000, 1500, 1500],
  statustext: "",
  is_hardware: false,
  port: "None",
  baud: 115200,
};

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  logEntry("INFO", `Connecting to telemetry bridge: ${wsUrl}`);
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    logEntry("INFO", "Telemetry link established with Pixhawk 2.4.8 bridge");
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "TELEMETRY" && msg.data) {
        updateTelemetry(msg.data);
      } else if (msg.type === "COMMAND_RESULT") {
        showNudgeBadge(msg.data.msg);
        logEntry(msg.data.ok ? "INFO" : "WARN", msg.data.msg);
      } else if (msg.type === "ALERT") {
        logEntry("CRIT", `ALERT: ${msg.data.message || msg.data}`);
      }
    } catch (e) {
      console.error("Telemetry parse error", e);
    }
  };

  ws.onclose = () => {
    updatePill("hud-hw-pill", "FC LINK LOST", "hud-pill--danger");
    logEntry("WARN", "Telemetry link dropped. Reconnecting in 2s...");
    setTimeout(connectWebSocket, 2000);
  };
}

function updateTelemetry(data) {
  telemetry = { ...telemetry, ...data };

  // Header metrics
  document.getElementById("val-flight-mode").innerText = telemetry.flight_mode;
  document.getElementById("val-alt").innerText = `${telemetry.alt.toFixed(2)} m (${(telemetry.alt * 3.28084).toFixed(1)} ft)`;
  document.getElementById("val-speed").innerText = `${telemetry.groundspeed.toFixed(1)} m/s`;
  document.getElementById("val-battery").innerText = `${telemetry.battery_v.toFixed(1)}V (${telemetry.battery_pct}%)`;
  document.getElementById("val-gps").innerText = `${telemetry.gps_sats} Sats (Fix ${telemetry.gps_fix})`;

  // Hardware status pill
  if (telemetry.is_hardware) {
    updatePill("hud-hw-pill", `HW: ${telemetry.port}`, "hud-pill--connected");
  } else {
    updatePill("hud-hw-pill", "SIMULATOR ACTIVE", "hud-pill--neutral");
  }

  // Arming status pill
  if (telemetry.armed) {
    updatePill("hud-arm-pill", "ARMED", "hud-pill--danger");
  } else {
    updatePill("hud-arm-pill", "DISARMED", "hud-pill--neutral");
  }

  // Control Authority Pill (GCS vs FlySky RC)
  if (telemetry.flight_mode === "GUIDED") {
    updatePill("hud-control-authority", "GCS GUIDED ACTIVE", "hud-pill--connected");
  } else if (["LOITER", "ALT_HOLD", "STABILIZE"].includes(telemetry.flight_mode)) {
    updatePill("hud-control-authority", `FLYSKY RC (${telemetry.flight_mode})`, "hud-pill--warning");
  } else {
    updatePill("hud-control-authority", telemetry.flight_mode, "hud-pill--neutral");
  }

  // Port and Statustext
  const portInfoEl = document.getElementById("val-port-info");
  if (portInfoEl) {
    portInfoEl.innerText = `${telemetry.port} @ ${telemetry.baud}`;
  }
  const statusTextEl = document.getElementById("val-statustext");
  if (statusTextEl && telemetry.statustext) {
    statusTextEl.innerText = telemetry.statustext;
  }

  // Artificial Horizon and Attitude degrees
  const pitchLadder = document.getElementById("hud-pitch-ladder");
  if (pitchLadder) {
    const pitchOffset = (telemetry.pitch || 0) * 80;
    const rollAngle = (telemetry.roll || 0) * (180 / Math.PI);
    pitchLadder.style.transform = `translateY(${pitchOffset}px) rotate(${rollAngle}deg)`;
  }

  const rollDeg = ((telemetry.roll || 0) * 180 / Math.PI).toFixed(1);
  const pitchDeg = ((telemetry.pitch || 0) * 180 / Math.PI).toFixed(1);
  const yawDeg = ((telemetry.yaw || 0) * 180 / Math.PI).toFixed(1);

  document.getElementById("val-roll").innerText = `${rollDeg}°`;
  document.getElementById("val-pitch").innerText = `${pitchDeg}°`;
  document.getElementById("val-yaw").innerText = `${yawDeg}°`;

  // FlySky RC Channel Bars
  if (telemetry.rc_channels && telemetry.rc_channels.length >= 6) {
    for (let i = 1; i <= 6; i++) {
      const pwm = telemetry.rc_channels[i - 1] || 1500;
      const barEl = document.getElementById(`rc-bar-${i}`);
      const valEl = document.getElementById(`rc-val-${i}`);
      if (barEl) {
        const pct = Math.max(0, Math.min(100, ((pwm - 1000) / 1000) * 100));
        barEl.style.width = `${pct}%`;
      }
      if (valEl) {
        valEl.innerText = pwm;
      }
    }
  }
}

function updatePill(id, text, className) {
  const el = document.getElementById(id);
  if (el) {
    el.innerText = text;
    el.className = `hud-pill ${className}`;
  }
}

function showNudgeBadge(text) {
  const badge = document.getElementById("hud-last-command");
  if (badge) {
    badge.innerText = text;
    badge.style.borderColor = "var(--color-hud-success)";
    badge.style.color = "var(--color-hud-success)";
    setTimeout(() => {
      badge.style.borderColor = "var(--color-hud-primary)";
      badge.style.color = "var(--color-hud-primary)";
    }, 2500);
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

  while (stream.children.length > 30) {
    stream.removeChild(stream.lastChild);
  }
}

function sendCommand(command, params = {}, confirm = false) {
  logEntry("INFO", `Command: ${command.toUpperCase()} ${JSON.stringify(params)}`);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ command, params, confirm }));
  } else {
    fetch("/api/v1/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, params, confirm }),
    })
      .then((res) => res.json())
      .then((data) => {
        showNudgeBadge(data.msg);
        logEntry(data.ok ? "INFO" : "WARN", data.msg);
      })
      .catch((err) => logEntry("CRIT", `Failed: ${err}`));
  }
}

function sendStep(axis) {
  const unitLabel = activeStepSize < 0.3 ? `${(activeStepSize * 100).toFixed(0)}cm` : `${(activeStepSize / 0.3048).toFixed(0)}ft`;
  showNudgeBadge(`Nudging ${axis.toUpperCase()} by ${unitLabel}...`);
  sendCommand("step", { axis, distance: activeStepSize });
}

async function loadSerialPorts() {
  try {
    const res = await fetch("/api/v1/ports");
    const data = await res.json();
    const sel = document.getElementById("sel-port");
    if (!sel || !data.ports) return;

    // Retain selected
    const curVal = sel.value;
    sel.innerHTML = '<option value="AUTO">AUTO-PROBE</option>';

    data.ports.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.device;
      opt.innerText = `${p.device} (${p.description.substring(0, 24)})`;
      sel.appendChild(opt);
    });

    if (curVal && [...sel.options].some((o) => o.value === curVal)) {
      sel.value = curVal;
    }
  } catch (e) {
    console.error("Failed to load serial ports", e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  connectWebSocket();
  loadSerialPorts();

  // Step size toggle buttons
  document.querySelectorAll(".hud-btn-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".hud-btn-toggle").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeStepSize = parseFloat(btn.getAttribute("data-step"));
      const label = activeStepSize < 0.3 ? `${(activeStepSize * 100).toFixed(0)} cm` : `${(activeStepSize / 0.3048).toFixed(0)} ft`;
      showNudgeBadge(`Step size selected: ${label}`);
      logEntry("INFO", `Step size configured to ${label} (${activeStepSize}m)`);
    });
  });

  // Keypad Stepper Buttons
  document.getElementById("btn-step-up")?.addEventListener("click", () => sendStep("up"));
  document.getElementById("btn-step-down")?.addEventListener("click", () => sendStep("down"));
  document.getElementById("btn-step-fwd")?.addEventListener("click", () => sendStep("forward"));
  document.getElementById("btn-step-back")?.addEventListener("click", () => sendStep("backward"));
  document.getElementById("btn-step-left")?.addEventListener("click", () => sendStep("left"));
  document.getElementById("btn-step-right")?.addEventListener("click", () => sendStep("right"));
  document.getElementById("btn-step-hold")?.addEventListener("click", () => sendCommand("hold"));
  document.getElementById("btn-step-yaw-l")?.addEventListener("click", () => sendStep("yaw_left"));
  document.getElementById("btn-step-yaw-r")?.addEventListener("click", () => sendStep("yaw_right"));

  // RC Handover & Mode Buttons
  document.getElementById("btn-handover-loiter")?.addEventListener("click", () => {
    sendCommand("rc_handover", { mode: "LOITER" });
  });
  document.getElementById("btn-handover-althold")?.addEventListener("click", () => {
    sendCommand("rc_handover", { mode: "ALT_HOLD" });
  });
  document.getElementById("btn-mode-guided")?.addEventListener("click", () => {
    sendCommand("mode", { mode: "GUIDED" });
  });
  document.getElementById("btn-mode-stabilize")?.addEventListener("click", () => {
    sendCommand("mode", { mode: "STABILIZE" });
  });

  // Core Flight Buttons
  document.getElementById("btn-arm")?.addEventListener("click", () => sendCommand("arm"));
  document.getElementById("btn-disarm")?.addEventListener("click", () => sendCommand("disarm"));
  document.getElementById("btn-takeoff")?.addEventListener("click", () => {
    const alt = prompt("Takeoff altitude in meters (e.g. 1.0 or 2.0):", "1.5");
    if (alt) sendCommand("takeoff", { altitude: parseFloat(alt) });
  });
  document.getElementById("btn-land")?.addEventListener("click", () => sendCommand("land"));
  document.getElementById("btn-rtl")?.addEventListener("click", () => sendCommand("rtl"));
  document.getElementById("btn-kill")?.addEventListener("click", () => {
    if (confirm("⚠️ EMERGENCY MOTOR KILL: Motors will stop immediately. Confirm?")) {
      sendCommand("kill", {}, true);
    }
  });

  // Serial Port Reconnect button
  document.getElementById("btn-reconnect")?.addEventListener("click", () => {
    const port = document.getElementById("sel-port")?.value || "AUTO";
    const baud = parseInt(document.getElementById("sel-baud")?.value || "115200");
    logEntry("INFO", `Initiating hardware connection to ${port} @ ${baud}...`);
    fetch("/api/v1/connection/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ port, baud }),
    })
      .then((res) => res.json())
      .then((d) => logEntry(d.ok ? "INFO" : "WARN", d.msg))
      .catch((e) => logEntry("CRIT", `Connection error: ${e}`));
  });

  // Motor Spin Test Controls
  let activeMotorThrottle = 10;
  let activeMotorDuration = 2;

  const sliderThrottle = document.getElementById("slider-motor-speed");
  const valThrottleTxt = document.getElementById("val-motor-speed-txt");

  if (sliderThrottle) {
    sliderThrottle.addEventListener("input", (e) => {
      activeMotorThrottle = parseInt(e.target.value);
      if (valThrottleTxt) {
        valThrottleTxt.innerText = `${activeMotorThrottle}% SPEED`;
      }
      document.querySelectorAll(".btn-speed-preset").forEach((b) => {
        if (parseInt(b.getAttribute("data-speed")) === activeMotorThrottle) {
          b.classList.add("active");
        } else {
          b.classList.remove("active");
        }
      });
    });
  }

  document.querySelectorAll(".btn-speed-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-speed-preset").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeMotorThrottle = parseInt(btn.getAttribute("data-speed"));
      if (sliderThrottle) sliderThrottle.value = activeMotorThrottle;
      if (valThrottleTxt) valThrottleTxt.innerText = `${activeMotorThrottle}% SPEED`;
      logEntry("INFO", `Motor test throttle set to ${activeMotorThrottle}%`);
    });
  });

  document.querySelectorAll(".btn-dur-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-dur-preset").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeMotorDuration = parseInt(btn.getAttribute("data-dur"));
      logEntry("INFO", `Motor test duration set to ${activeMotorDuration}s`);
    });
  });

  function triggerMotorTest(motorNum) {
    const motorName = motorNum === 0 ? "ALL MOTORS (Sequence)" : `MOTOR ${motorNum}`;
    showNudgeBadge(`Spinning ${motorName} at ${activeMotorThrottle}%...`);
    logEntry("INFO", `Testing ${motorName} @ ${activeMotorThrottle}% throttle for ${activeMotorDuration}s`);
    sendCommand("motor_test", {
      motor: motorNum,
      throttle: activeMotorThrottle,
      duration: activeMotorDuration,
    });
  }

  document.getElementById("btn-test-m1")?.addEventListener("click", () => triggerMotorTest(1));
  document.getElementById("btn-test-m2")?.addEventListener("click", () => triggerMotorTest(2));
  document.getElementById("btn-test-m3")?.addEventListener("click", () => triggerMotorTest(3));
  document.getElementById("btn-test-m4")?.addEventListener("click", () => triggerMotorTest(4));
  document.getElementById("btn-test-all-motors")?.addEventListener("click", () => triggerMotorTest(0));
  document.getElementById("btn-test-stop-motors")?.addEventListener("click", () => {
    showNudgeBadge("STOPPING ALL MOTORS");
    sendCommand("motor_test", { motor: 1, throttle: 0, duration: 0 });
  });
});
