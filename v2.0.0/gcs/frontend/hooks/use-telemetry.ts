"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  TelemetryData,
  TelemetryHistoryPoint,
  LogEntry,
  SerialPortInfo,
  CommandResult,
  WaypointItem,
} from "@/types/telemetry";

const DEFAULT_TELEMETRY: TelemetryData = {
  armed: false,
  lat: 28.6139,
  lon: 77.2090,
  alt: 0.0,
  heading: 0.0,
  groundspeed: 0.0,
  battery_v: 0.0,
  battery_pct: 0,
  gps_fix: 0,
  gps_sats: 0,
  flight_mode: "STABILIZE",
  pitch: 0.0,
  roll: 0.0,
  yaw: 0.0,
  rc_channels: [1500, 1500, 1100, 1500, 1000, 1000, 1500, 1500],
  statustext: "Initializing GCS telemetry bridge...",
  is_hardware: false,
  port: "None",
  baud: 115200,
};

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<TelemetryData>(DEFAULT_TELEMETRY);
  const [history, setHistory] = useState<TelemetryHistoryPoint[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<[number, number][]>([]);
  const [connected, setConnected] = useState<boolean>(false);
  const [ports, setPorts] = useState<SerialPortInfo[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastCommand, setLastCommand] = useState<CommandResult | null>(null);
  const [activeStepSize, setActiveStepSize] = useState<number>(0.3048); // 1 ft default

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const addLog = useCallback((level: "INFO" | "WARN" | "CRIT", message: string) => {
    const timeStr = new Date().toTimeString().split(" ")[0];
    const newEntry: LogEntry = {
      id: `${Date.now()}-${Math.random()}`,
      timestamp: timeStr,
      level,
      message,
    };
    setLogs((prev) => [newEntry, ...prev.slice(0, 49)]);
  }, []);

  // Fetch Serial Ports
  const fetchPorts = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/ports");
      if (res.ok) {
        const data = await res.json();
        setPorts(data.ports || []);
      }
    } catch {
      // Backend may still be offline
    }
  }, []);

  // WebSocket Connection
  const connectWs = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
    const wsUrl = `ws://${host}:8000/ws/telemetry`;

    addLog("INFO", `Connecting to telemetry bridge: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      addLog("INFO", "Telemetry link established with Pixhawk 2.4.8 bridge");
      fetchPorts();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "TELEMETRY" && msg.data) {
          const data: TelemetryData = msg.data;
          setTelemetry((prev) => ({ ...prev, ...data }));

          // Append to history for analytics (keep max 60 points)
          setHistory((prev) => {
            const point: TelemetryHistoryPoint = {
              timestamp: Date.now(),
              alt: data.alt || 0,
              groundspeed: data.groundspeed || 0,
              battery_v: data.battery_v || 0,
              pitch: data.pitch || 0,
              roll: data.roll || 0,
              yaw: data.yaw || 0,
              heading: data.heading || 0,
            };
            return [...prev.slice(-59), point];
          });

          // Append to breadcrumbs if coordinates are valid
          if (data.lat && data.lon && (data.lat !== 0 || data.lon !== 0)) {
            setBreadcrumbs((prev) => {
              const last = prev[prev.length - 1];
              if (!last || Math.abs(last[0] - data.lat) > 0.00001 || Math.abs(last[1] - data.lon) > 0.00001) {
                return [...prev.slice(-199), [data.lat, data.lon]];
              }
              return prev;
            });
          }
        } else if (msg.type === "COMMAND_RESULT" && msg.data) {
          setLastCommand({ ok: msg.data.ok, msg: msg.data.msg, timestamp: Date.now() });
          addLog(msg.data.ok ? "INFO" : "WARN", msg.data.msg);
        } else if (msg.type === "ALERT" && msg.data) {
          addLog("CRIT", `ALERT: ${msg.data.message || msg.data}`);
        }
      } catch (err) {
        console.error("Telemetry parse error", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      addLog("WARN", "Telemetry link disconnected. Reconnecting in 3s...");
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = setTimeout(connectWs, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [addLog, fetchPorts]);

  useEffect(() => {
    connectWs();
    fetchPorts();
    const portInterval = setInterval(fetchPorts, 10000);

    return () => {
      clearInterval(portInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWs, fetchPorts]);

  // Send Command via WebSocket or REST fallback
  const sendCommand = useCallback(
    async (command: string, params: Record<string, any> = {}, confirm = false) => {
      addLog("INFO", `TX Command: ${command.toUpperCase()}`);

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ command, params, confirm }));
      } else {
        try {
          const res = await fetch("http://localhost:8000/api/v1/command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command, params, confirm }),
          });
          const data = await res.json();
          setLastCommand({ ok: data.ok, msg: data.msg, timestamp: Date.now() });
          addLog(data.ok ? "INFO" : "WARN", data.msg);
        } catch (err) {
          addLog("CRIT", `Command failed to transmit: ${err}`);
        }
      }
    },
    [addLog]
  );

  // Send Step Nudge
  const sendStep = useCallback(
    (axis: string) => {
      const unitLabel = activeStepSize < 0.3 ? `${(activeStepSize * 100).toFixed(0)}cm` : `${(activeStepSize / 0.3048).toFixed(0)}ft`;
      setLastCommand({ ok: true, msg: `Nudge ${axis.toUpperCase()} by ${unitLabel}...`, timestamp: Date.now() });
      sendCommand("step", { axis, distance: activeStepSize });
    },
    [activeStepSize, sendCommand]
  );

  // Set Flight Mode
  const setFlightMode = useCallback(
    (mode: string) => {
      sendCommand("mode", { mode });
    },
    [sendCommand]
  );

  // Connect Serial Hardware
  const connectSerial = useCallback(
    async (port: string, baud: number) => {
      addLog("INFO", `Connecting to hardware ${port} @ ${baud}...`);
      try {
        const res = await fetch("http://localhost:8000/api/v1/connection/connect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ port, baud }),
        });
        const d = await res.json();
        addLog(d.ok ? "INFO" : "WARN", d.msg);
        fetchPorts();
      } catch (err) {
        addLog("CRIT", `Connection failed: ${err}`);
      }
    },
    [addLog, fetchPorts]
  );

  // Motor Spin Test
  // Motor Spin Test
  const testMotor = useCallback(
    (motor: number, throttle: number, duration: number) => {
      sendCommand("motor_test", { motor, throttle, duration });
    },
    [sendCommand]
  );

  // ArduPilot One-Click Auto Setup
  const runArduPilotAutoSetup = useCallback(
    async (profile: "bench" | "field" = "bench", calibrateSensors = true, rtlAltitude = 15.0): Promise<any> => {
      addLog("INFO", `Executing ArduPilot Auto-Setup [${profile.toUpperCase()}]...`);
      try {
        const res = await fetch("http://localhost:8000/api/v1/ardupilot/auto_setup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ profile, calibrate_sensors: calibrateSensors, rtl_altitude_m: rtlAltitude }),
        });
        const d = await res.json();
        addLog(d.ok ? "INFO" : "WARN", d.msg);
        return d;
      } catch (err) {
        addLog("CRIT", `Auto-Setup request failed: ${err}`);
        return { ok: false, msg: String(err) };
      }
    },
    [addLog]
  );

  // Fetch ArduPilot Parameters
  const fetchArduPilotParams = useCallback(async (): Promise<any[]> => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/ardupilot/params");
      if (res.ok) {
        const d = await res.json();
        return d.params || [];
      }
    } catch (err) {
      console.error("Fetch params failed", err);
    }
    return [];
  }, []);

  // Set ArduPilot Parameter
  const setArduPilotParam = useCallback(
    async (name: string, value: number): Promise<boolean> => {
      addLog("INFO", `Writing param ${name} = ${value} to Pixhawk...`);
      try {
        const res = await fetch("http://localhost:8000/api/v1/ardupilot/params/set", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, value }),
        });
        const d = await res.json();
        addLog(d.ok ? "INFO" : "WARN", d.msg);
        return d.ok;
      } catch (err) {
        addLog("CRIT", `Set param error: ${err}`);
        return false;
      }
    },
    [addLog]
  );

  // Pre-Arm Sanity Readiness Check
  const fetchPrearmCheck = useCallback(async (): Promise<any> => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/ardupilot/prearm_check");
      if (res.ok) {
        const d = await res.json();
        return d.data;
      }
    } catch (err) {
      console.error("Prearm check error", err);
    }
    return null;
  }, []);

  // Generate Autonomous Lawnmower Survey Waypoints
  const generateSurveyWaypoints = useCallback(
    async (polygon: [number, number][], altitude = 15.0, laneSpacing = 15.0): Promise<WaypointItem[]> => {
      addLog("INFO", `Generating survey grid: ${laneSpacing}m lane spacing @ ${altitude}m...`);
      try {
        const res = await fetch("http://localhost:8000/api/v1/mission/generate_survey", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ polygon, altitude, lane_spacing_m: laneSpacing }),
        });
        const d = await res.json();
        if (d.ok && d.waypoints) {
          addLog("INFO", `Generated ${d.count} survey waypoints`);
          return d.waypoints;
        }
      } catch (err) {
        addLog("CRIT", `Survey generation error: ${err}`);
      }
      return [];
    },
    [addLog]
  );

  return {
    telemetry,
    history,
    breadcrumbs,
    connected,
    ports,
    logs,
    lastCommand,
    activeStepSize,
    setActiveStepSize,
    sendCommand,
    sendStep,
    setFlightMode,
    connectSerial,
    testMotor,
    fetchPorts,
    addLog,
    runArduPilotAutoSetup,
    fetchArduPilotParams,
    setArduPilotParam,
    fetchPrearmCheck,
    generateSurveyWaypoints,
  };
}
