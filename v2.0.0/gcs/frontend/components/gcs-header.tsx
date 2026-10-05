"use client";

import { Button, Card, Chip } from "@heroui/react";
import { TelemetryData } from "@/types/telemetry";
import { ThemeSwitch } from "@/components/theme-switch";
import { Plane, Cpu, Wifi, WifiOff, Battery, Satellite, Gauge, Wrench } from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface GcsHeaderProps {
  telemetry: TelemetryData;
  connected: boolean;
  onOpenCalibration?: () => void;
}

export default function GcsHeader({ telemetry, connected, onOpenCalibration }: GcsHeaderProps) {
  const isGuided = telemetry.flight_mode === "GUIDED";
  const batteryLow = telemetry.battery_v < 10.5;

  return (
    <header className="w-full flex flex-col gap-2.5 p-3 bg-surface border-b border-border shadow-lg backdrop-blur-sm">
      {/* Top Callsign and Status Cluster */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Callsign */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-accent/10 rounded-lg border border-accent/30">
            <Plane className="w-4 h-4 text-accent" />
            <span className="font-mono text-xs font-black tracking-wider text-accent">
              GUARDIA AI v2.0.0
            </span>
          </div>

          {/* Connection Status */}
          <GcsTooltip content={connected ? "WebSocket link active — 5Hz telemetry" : "No connection to backend bridge"}>
            <Chip
              size="sm"
              variant="soft"
              color={connected ? "success" : "danger"}
              className="font-mono text-[10px] font-semibold cursor-help"
            >
              <span className="flex items-center gap-1.5">
                {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                {connected ? "LINK OK" : "LINK LOST"}
              </span>
            </Chip>
          </GcsTooltip>

          {/* Hardware status pill */}
          <GcsTooltip content={telemetry.is_hardware ? `Connected via ${telemetry.port}` : "Running in software simulator mode"}>
            <Chip
              size="sm"
              variant="soft"
              color={telemetry.is_hardware ? "accent" : "default"}
              className="font-mono text-[10px] cursor-help"
            >
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3 h-3" />
                {telemetry.is_hardware ? `HW: ${telemetry.port}` : "SIMULATOR"}
              </span>
            </Chip>
          </GcsTooltip>

          {/* Arm Status Pill */}
          <Chip
            size="sm"
            variant={telemetry.armed ? "primary" : "soft"}
            color={telemetry.armed ? "danger" : "default"}
            className={`font-mono text-[10px] font-black tracking-wider ${
              telemetry.armed ? "animate-pulse shadow-md shadow-danger/20" : ""
            }`}
          >
            {telemetry.armed ? "ARMED — MOTORS LIVE" : "DISARMED"}
          </Chip>

          {/* Flight Mode */}
          <Chip
            size="sm"
            variant="soft"
            color="accent"
            className="font-mono text-[10px] font-bold"
          >
            MODE: {telemetry.flight_mode}
          </Chip>

          {/* Control Authority */}
          <Chip
            size="sm"
            variant="secondary"
            color={isGuided ? "accent" : "warning"}
            className="font-mono text-[10px]"
          >
            {isGuided ? "GCS CONTROL" : `FLYSKY RC (${telemetry.flight_mode})`}
          </Chip>
        </div>

        {/* Right side tools */}
        <div className="flex items-center gap-2">
          {onOpenCalibration && (
            <Button
              size="sm"
              variant="outline"
              className="font-mono text-xs font-semibold gap-1.5 h-8 border-accent/40 hover:bg-accent/10 text-accent"
              onPress={onOpenCalibration}
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>Calibrate & Setup</span>
            </Button>
          )}
          <ThemeSwitch />
        </div>
      </div>

      {/* Primary Telemetry Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <GcsTooltip content="Altitude above takeoff point (barometric)">
          <Card className="bg-surface-secondary border border-border shadow-none hover:border-accent/40 transition-colors cursor-help">
            <div className="flex items-center gap-2.5 px-3 py-2">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                <Gauge className="w-4 h-4 text-accent" />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-muted font-mono uppercase tracking-wider">Altitude</span>
                <span className="font-mono font-bold text-sm text-foreground leading-tight">
                  {telemetry.alt.toFixed(2)}
                  <span className="text-muted text-[10px] ml-1">m</span>
                </span>
                <span className="text-muted text-[9px] font-mono">({(telemetry.alt * 3.28084).toFixed(1)} ft)</span>
              </div>
            </div>
          </Card>
        </GcsTooltip>

        <GcsTooltip content="Ground speed relative to terrain">
          <Card className="bg-surface-secondary border border-border shadow-none hover:border-accent/40 transition-colors cursor-help">
            <div className="flex items-center gap-2.5 px-3 py-2">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                <Plane className="w-4 h-4 text-accent" />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-muted font-mono uppercase tracking-wider">Groundspeed</span>
                <span className="font-mono font-bold text-sm text-foreground leading-tight">
                  {telemetry.groundspeed.toFixed(1)}
                  <span className="text-muted text-[10px] ml-1">m/s</span>
                </span>
                <span className="text-muted text-[9px] font-mono">({(telemetry.groundspeed * 3.6).toFixed(1)} km/h)</span>
              </div>
            </div>
          </Card>
        </GcsTooltip>

        <GcsTooltip content={`3S LiPo — ${batteryLow ? "LOW BATTERY WARNING" : "Nominal voltage"}`}>
          <Card className={`border shadow-none transition-colors cursor-help ${
            batteryLow
              ? "bg-danger/10 border-danger/40 hover:border-danger/60"
              : "bg-surface-secondary border-border hover:border-success/40"
          }`}>
            <div className="flex items-center gap-2.5 px-3 py-2">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                batteryLow ? "bg-danger/20" : "bg-success/10"
              }`}>
                <Battery className={`w-4 h-4 ${
                  batteryLow ? "text-danger animate-bounce" : "text-success"
                }`} />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-muted font-mono uppercase tracking-wider">3S LiPo</span>
                <span className={`font-mono font-bold text-sm leading-tight ${
                  batteryLow ? "text-danger" : "text-foreground"
                }`}>
                  {telemetry.battery_v.toFixed(1)}
                  <span className="text-muted text-[10px] ml-1">V</span>
                </span>
                <span className="text-muted text-[9px] font-mono">({telemetry.battery_pct}%)</span>
              </div>
            </div>
          </Card>
        </GcsTooltip>

        <GcsTooltip content={`GPS Fix Type: ${telemetry.gps_fix >= 3 ? "3D Fix" : telemetry.gps_fix === 2 ? "2D Fix" : "No Fix"}`}>
          <Card className="bg-surface-secondary border border-border shadow-none hover:border-accent/40 transition-colors cursor-help">
            <div className="flex items-center gap-2.5 px-3 py-2">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                <Satellite className="w-4 h-4 text-accent" />
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] text-muted font-mono uppercase tracking-wider">M8N GPS</span>
                <span className="font-mono font-bold text-sm text-foreground leading-tight">
                  {telemetry.gps_sats}
                  <span className="text-muted text-[10px] ml-1">Sats</span>
                </span>
                <Chip size="sm" variant="soft" color={telemetry.gps_fix >= 3 ? "success" : "warning"} className="h-4 text-[8px] font-mono mt-0.5">
                  Fix {telemetry.gps_fix}
                </Chip>
              </div>
            </div>
          </Card>
        </GcsTooltip>
      </div>
    </header>
  );
}
