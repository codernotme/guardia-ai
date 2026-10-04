/**
 * Guardia AI v2.0.0 — GCS Telemetry & Command Types
 */

export interface TelemetryData {
  state?: string;
  mission?: string;
  armed: boolean;
  lat: number;
  lon: number;
  alt: number;
  heading: number;
  groundspeed: number;
  battery_v: number;
  battery_pct: number;
  gps_fix: number;
  gps_sats: number;
  target_id?: number | null;
  target_locked?: boolean;
  targets_detected?: number;
  cpu_temp?: number;
  ram_mb?: number;
  uptime?: number;
  flight_mode: string;
  pitch: number;
  roll: number;
  yaw: number;
  rc_channels: number[];
  statustext: string;
  is_hardware: boolean;
  port: string;
  baud: number;
}

export interface TelemetryHistoryPoint {
  timestamp: number;
  alt: number;
  groundspeed: number;
  battery_v: number;
  pitch: number;
  roll: number;
  yaw: number;
  heading: number;
}

export interface SerialPortInfo {
  device: string;
  description: string;
  hwid?: string;
}

export interface CommandResult {
  ok: boolean;
  msg: string;
  timestamp?: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "INFO" | "WARN" | "CRIT";
  message: string;
}

export interface WaypointItem {
  id: string;
  lat: number;
  lon: number;
  alt: number;
  speed: number;
}
