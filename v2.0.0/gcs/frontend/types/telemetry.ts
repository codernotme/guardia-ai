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

export interface ArduPilotParam {
  name: string;
  category: string;
  value: number;
  default: number;
  description: string;
  options?: number[];
}

export interface PrearmCheckItem {
  name: string;
  status: "PASS" | "WARN" | "FAIL" | "READY";
  detail: string;
}

export interface PrearmReport {
  ready: boolean;
  score: number;
  checks: PrearmCheckItem[];
  timestamp: number;
}

export interface AutoSetupStep {
  step: string;
  description: string;
  ok: boolean;
  detail: string;
}

export interface AutoSetupReport {
  ok: boolean;
  msg: string;
  data?: {
    profile: string;
    steps: AutoSetupStep[];
  };
}

export interface FieldSector {
  id: string;
  name: string;
  code: string;
  areaSqm: number;
  location: string;
  group: string;
  roi: string;
  cropType: string;
  plantingDate: string;
  harvestDate: string;
  health: number; // 0-100
  status: "active" | "standby" | "alert";
  polygon: [number, number][];
}
