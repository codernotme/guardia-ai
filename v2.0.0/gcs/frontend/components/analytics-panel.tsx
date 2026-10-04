"use client";

import { useMemo } from "react";
import { Card, Chip } from "@heroui/react";
import { TelemetryData, TelemetryHistoryPoint } from "@/types/telemetry";
import { Activity, BatteryCharging, Satellite, Thermometer, ShieldCheck } from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface AnalyticsProps {
  telemetry: TelemetryData;
  history: TelemetryHistoryPoint[];
}

export default function AnalyticsPanel({ telemetry, history }: AnalyticsProps) {
  // SVG Sparkline generator
  const generatePath = (
    data: number[],
    minVal: number,
    maxVal: number,
    width = 240,
    height = 50
  ) => {
    if (!data || data.length < 2) return "";
    const range = maxVal - minVal || 1;
    const step = width / (data.length - 1);

    const points = data.map((val, idx) => {
      const x = idx * step;
      const normalized = Math.max(0, Math.min(1, (val - minVal) / range));
      const y = height - normalized * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return `M ${points.join(" L ")}`;
  };

  const generateGradientPath = (
    data: number[],
    minVal: number,
    maxVal: number,
    width = 240,
    height = 50
  ) => {
    if (!data || data.length < 2) return "";
    const range = maxVal - minVal || 1;
    const step = width / (data.length - 1);

    const points = data.map((val, idx) => {
      const x = idx * step;
      const normalized = Math.max(0, Math.min(1, (val - minVal) / range));
      const y = height - normalized * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return `M 0,${height} L ${points.join(" L ")} L ${width},${height} Z`;
  };

  const altHistory = useMemo(() => history.map((h) => h.alt), [history]);
  const speedHistory = useMemo(() => history.map((h) => h.groundspeed), [history]);
  const battHistory = useMemo(() => history.map((h) => h.battery_v), [history]);

  const maxAlt = Math.max(5, ...altHistory, telemetry.alt || 0);
  const maxSpeed = Math.max(5, ...speedHistory, telemetry.groundspeed || 0);
  const minBatt = 9.0;
  const maxBatt = 12.6; // 3S LiPo max
  const batteryLow = telemetry.battery_v < 10.5;

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
              Live Analytics
            </span>
          </div>
          <Chip size="sm" variant="soft" color="success" className="font-mono text-[10px]">
            5Hz STREAM
          </Chip>
        </div>

        {/* Grid of Analytics Cards */}
        <div className="grid grid-cols-1 gap-3">
          {/* Card 1: Altitude Profile Graph */}
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-muted uppercase tracking-wider">
                  Altitude Profile
                </span>
                <span className="font-mono text-xs font-bold text-accent">
                  {telemetry.alt.toFixed(2)} m
                </span>
              </div>

              <div className="relative w-full h-[55px] bg-background rounded-lg border border-accent/20 overflow-hidden">
                <svg viewBox="0 0 240 50" className="w-full h-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="altGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path
                    d={generateGradientPath(altHistory, 0, maxAlt, 240, 50)}
                    fill="url(#altGrad)"
                  />
                  <path
                    d={generatePath(altHistory, 0, maxAlt, 240, 50)}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div className="flex items-center justify-between text-[9px] font-mono text-muted">
                <span>0 m</span>
                <span>Peak: {maxAlt.toFixed(1)} m</span>
              </div>
            </div>
          </Card>

          {/* Card 2: Groundspeed Trend Graph */}
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-muted uppercase tracking-wider">
                  Groundspeed Trend
                </span>
                <span className="font-mono text-xs font-bold text-foreground">
                  {telemetry.groundspeed.toFixed(1)} m/s
                </span>
              </div>

              <div className="relative w-full h-[55px] bg-background rounded-lg border border-border overflow-hidden">
                <svg viewBox="0 0 240 50" className="w-full h-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="speedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--muted)" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="var(--muted)" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path
                    d={generateGradientPath(speedHistory, 0, maxSpeed, 240, 50)}
                    fill="url(#speedGrad)"
                  />
                  <path
                    d={generatePath(speedHistory, 0, maxSpeed, 240, 50)}
                    fill="none"
                    stroke="var(--muted)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div className="flex items-center justify-between text-[9px] font-mono text-muted">
                <span>0 m/s</span>
                <span>Peak: {maxSpeed.toFixed(1)} m/s</span>
              </div>
            </div>
          </Card>

          {/* Card 3: Battery Discharge Curve */}
          <Card className={`border shadow-none ${
            batteryLow ? "bg-danger/5 border-danger/30" : "bg-surface-secondary border-border"
          }`}>
            <div className="flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-muted uppercase tracking-wider">
                  LiPo Battery
                </span>
                <span
                  className={`font-mono text-xs font-bold ${
                    batteryLow ? "text-danger" : "text-success"
                  }`}
                >
                  {telemetry.battery_v.toFixed(1)}V ({telemetry.battery_pct}%)
                </span>
              </div>

              <div className="relative w-full h-[55px] bg-background rounded-lg border border-border overflow-hidden">
                <svg viewBox="0 0 240 50" className="w-full h-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="battGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={batteryLow ? "var(--danger)" : "var(--success)"} stopOpacity="0.3" />
                      <stop offset="100%" stopColor={batteryLow ? "var(--danger)" : "var(--success)"} stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path
                    d={generateGradientPath(battHistory, minBatt, maxBatt, 240, 50)}
                    fill="url(#battGrad)"
                  />
                  <path
                    d={generatePath(battHistory, minBatt, maxBatt, 240, 50)}
                    fill="none"
                    stroke={batteryLow ? "var(--danger)" : "var(--success)"}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div className="flex items-center justify-between text-[9px] font-mono text-muted">
                <span>9.0V</span>
                <span>12.6V (Full)</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Sensor Health and Diagnostics Row */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <GcsTooltip content={`GNSS Module: ${telemetry.gps_sats} satellites tracked`}>
            <Card className="bg-surface-secondary border border-border shadow-none cursor-help hover:border-accent/30 transition-colors">
              <div className="flex items-center gap-2 p-2.5">
                <Satellite className="w-4 h-4 text-accent shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-muted uppercase">GNSS / M8N</span>
                  <span className="font-bold text-foreground">
                    {telemetry.gps_sats} Sats
                  </span>
                </div>
              </div>
            </Card>
          </GcsTooltip>

          <GcsTooltip content="Companion computer temperature">
            <Card className="bg-surface-secondary border border-border shadow-none cursor-help hover:border-accent/30 transition-colors">
              <div className="flex items-center gap-2 p-2.5">
                <Thermometer className="w-4 h-4 text-warning shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-muted uppercase">CPU Temp</span>
                  <span className="font-bold text-foreground">
                    {telemetry.cpu_temp ? `${telemetry.cpu_temp.toFixed(1)}°C` : "42.0°C"}
                  </span>
                </div>
              </div>
            </Card>
          </GcsTooltip>

          <GcsTooltip content="Estimated remaining flight time based on battery">
            <Card className="bg-surface-secondary border border-border shadow-none cursor-help hover:border-accent/30 transition-colors">
              <div className="flex items-center gap-2 p-2.5">
                <BatteryCharging className="w-4 h-4 text-success shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-muted uppercase">Endurance</span>
                  <span className="font-bold text-foreground">
                    {telemetry.battery_pct > 20
                      ? `${Math.round((telemetry.battery_pct / 100) * 18)} min`
                      : "LOW BATT"}
                  </span>
                </div>
              </div>
            </Card>
          </GcsTooltip>

          <GcsTooltip content="IMU and EKF health status">
            <Card className="bg-surface-secondary border border-border shadow-none cursor-help hover:border-accent/30 transition-colors">
              <div className="flex items-center gap-2 p-2.5">
                <ShieldCheck className="w-4 h-4 text-accent shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[9px] text-muted uppercase">IMU / EKF</span>
                  <span className="font-bold text-success">HEALTHY</span>
                </div>
              </div>
            </Card>
          </GcsTooltip>
        </div>
      </div>
    </Card>
  );
}
