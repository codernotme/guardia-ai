"use client";

import React, { useState } from "react";
import { Card, Chip, Button, Tooltip } from "@heroui/react";
import {
  ChevronLeft,
  MoreVertical,
  Layers,
  TrendingUp,
  Droplets,
  Thermometer,
  Activity,
  Gauge,
  CloudSun,
  Sparkles,
  Plane,
  Battery,
  Satellite,
  Compass,
} from "lucide-react";
import { TelemetryData } from "@/types/telemetry";

interface FieldMetricsPanelProps {
  telemetry: TelemetryData;
  onSelectSector?: (sectorId: string) => void;
  onOpenAiInsights?: () => void;
}

export default function FieldMetricsPanel({
  telemetry,
  onSelectSector,
  onOpenAiInsights,
}: FieldMetricsPanelProps) {
  // Toggle between Agriculture Field view & Tactical Drone Telemetry view
  const [metricMode, setMetricMode] = useState<"agriculture" | "flight">("agriculture");
  const [forecastCondition, setForecastCondition] = useState<"standard" | "wind" | "radiation">("standard");

  return (
    <div className="w-full flex flex-col gap-3 font-sans select-none">
      {/* Top Breadcrumb & Active Sector Count */}
      <div className="flex items-center justify-between px-1">
        <button
          onClick={() => setMetricMode((prev) => (prev === "agriculture" ? "flight" : "agriculture"))}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface border border-border text-foreground hover:bg-surface-secondary transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-muted" />
          <span>{metricMode === "agriculture" ? "Switch to Drone HUD" : "Switch to Field Read"}</span>
        </button>

        <div className="flex items-center gap-2">
          <Chip
            size="sm"
            variant="soft"
            color="success"
            className="font-medium text-xs h-7 px-2.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 inline-block animate-pulse" />
            3 Fields active
          </Chip>

          <Button
            isIconOnly
            size="sm"
            variant="ghost"
            className="h-8 w-8 min-w-0 text-muted hover:text-foreground"
            aria-label="Options"
          >
            <MoreVertical className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main Sector Title Card */}
      <Card className="p-4 bg-surface border border-border shadow-sm rounded-2xl flex flex-col gap-2">
        <div className="flex items-start justify-between">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-foreground tracking-tight">
                Stanfield Land
              </h2>
              <Layers className="w-4 h-4 text-muted" />
            </div>
            <p className="text-xs text-muted mt-0.5">
              Texas, USA · Sahara Group
            </p>
          </div>

          <div className="flex flex-col items-end">
            <span className="text-sm font-bold text-foreground">
              12,123 sqm
            </span>
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5">
              <TrendingUp className="w-3 h-3" />
              ROI 12%
            </span>
          </div>
        </div>
      </Card>

      {/* 2x2 Metric Cards (Agri / Drone Telemetry) */}
      <div className="grid grid-cols-2 gap-2.5">
        {metricMode === "agriculture" ? (
          <>
            {/* Avg Humidity */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Avg Humidity</span>
                <Droplets className="w-4 h-4 text-muted" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">12%</span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Max <strong className="text-foreground">80%</strong></span>
                  <span>Min <strong className="text-foreground">10%</strong></span>
                </div>
              </div>
            </Card>

            {/* Avg Temperature */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Avg Temperature</span>
                <Thermometer className="w-4 h-4 text-muted" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">32°C</span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Max <strong className="text-foreground">42°</strong></span>
                  <span>Min <strong className="text-foreground">19°</strong></span>
                </div>
              </div>
            </Card>

            {/* Avg Soil Moisture */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Avg Soil Moisture</span>
                <Droplets className="w-4 h-4 text-muted" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">43kPa</span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Max <strong className="text-foreground">10kPa</strong></span>
                  <span>Min <strong className="text-foreground">61kPa</strong></span>
                </div>
              </div>
            </Card>

            {/* Avg pH Level */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Avg pH Level</span>
                <Activity className="w-4 h-4 text-muted" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">2.5</span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Max <strong className="text-foreground">4.6</strong></span>
                  <span>Min <strong className="text-foreground">1.2</strong></span>
                </div>
              </div>
            </Card>
          </>
        ) : (
          <>
            {/* Live Drone Altitude */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Altitude (AGL)</span>
                <Gauge className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">
                  {telemetry.alt.toFixed(1)}m
                </span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Feet <strong className="text-foreground">{(telemetry.alt * 3.28).toFixed(0)}ft</strong></span>
                  <span>Target <strong className="text-foreground">15m</strong></span>
                </div>
              </div>
            </Card>

            {/* Groundspeed */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">Groundspeed</span>
                <Plane className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">
                  {telemetry.groundspeed.toFixed(1)}m/s
                </span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Kmh <strong className="text-foreground">{(telemetry.groundspeed * 3.6).toFixed(0)}</strong></span>
                  <span>Wind <strong className="text-foreground">3 kt</strong></span>
                </div>
              </div>
            </Card>

            {/* Battery */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">LiPo Battery</span>
                <Battery className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">
                  {telemetry.battery_v > 0 ? telemetry.battery_v.toFixed(1) : "16.4"}V
                </span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Percent <strong className="text-foreground">{telemetry.battery_pct}%</strong></span>
                  <span>Health <strong className="text-emerald-500">Good</strong></span>
                </div>
              </div>
            </Card>

            {/* GPS Satellites */}
            <Card className="p-3 bg-surface border border-border shadow-sm rounded-2xl flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted font-medium">GPS / Navigation</span>
                <Satellite className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-foreground">
                  {telemetry.gps_sats > 0 ? telemetry.gps_sats : 12} Sats
                </span>
                <div className="flex flex-col items-end text-[10px] text-muted leading-tight">
                  <span>Fix <strong className="text-foreground">{telemetry.gps_fix >= 3 ? "3D Lock" : "Nominal"}</strong></span>
                  <span>HDOP <strong className="text-foreground">0.8</strong></span>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      {/* Area Prediction Model (Bar Chart) */}
      <Card className="p-4 bg-surface border border-border shadow-sm rounded-2xl flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground">Area prediction model</span>
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            Good for planting
          </span>
        </div>

        {/* Gradient Bar Chart representation */}
        <div className="flex items-end gap-1 h-12 w-full pt-2">
          {[
            { height: "45%", color: "bg-red-400" },
            { height: "50%", color: "bg-red-400" },
            { height: "55%", color: "bg-red-400" },
            { height: "60%", color: "bg-amber-400" },
            { height: "65%", color: "bg-amber-400" },
            { height: "68%", color: "bg-amber-400" },
            { height: "70%", color: "bg-amber-400" },
            { height: "74%", color: "bg-emerald-400" },
            { height: "80%", color: "bg-emerald-400" },
            { height: "85%", color: "bg-emerald-400" },
            { height: "92%", color: "bg-emerald-500" },
            { height: "98%", color: "bg-emerald-500" },
            { height: "100%", color: "bg-emerald-500" },
            { height: "85%", color: "bg-emerald-400" },
            { height: "78%", color: "bg-emerald-400" },
            { height: "72%", color: "bg-emerald-400" },
            { height: "68%", color: "bg-emerald-400" },
          ].map((bar, idx) => (
            <div
              key={idx}
              className="flex-1 bg-surface-secondary rounded-t-sm overflow-hidden flex flex-col justify-end h-full"
            >
              <div
                className={`w-full rounded-t-sm transition-all duration-500 ${bar.color}`}
                style={{ height: bar.height }}
              />
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[11px]">
          <span className="text-muted">12% production increase base on projection</span>
          <button
            onClick={onOpenAiInsights}
            className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold hover:bg-emerald-500/20 transition-colors"
          >
            <Sparkles className="w-3 h-3 text-emerald-500" />
            <span>AI Insights</span>
          </button>
        </div>
      </Card>

      {/* Soil Condition / Battery Discharge Graph */}
      <Card className="p-4 bg-surface border border-border shadow-sm rounded-2xl flex flex-col gap-2 relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground">Soil condition</span>
          <Chip
            size="sm"
            variant="secondary"
            className="bg-[#1A1D20] text-white text-[10px] font-medium h-5 px-2"
          >
            ≈ 90% Water
          </Chip>
        </div>

        {/* Stepped timeline graph */}
        <div className="h-16 w-full flex items-end justify-between gap-1 pt-3 pb-1 relative">
          <svg className="absolute inset-0 w-full h-full overflow-visible" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points="10,48 45,45 80,38 120,26 160,20 200,16 240,24 280,35 320,44"
            />
          </svg>
          {/* Stepped blocks beneath */}
          <div className="w-full flex items-end justify-between gap-1 h-full z-10 opacity-75">
            {[20, 25, 30, 45, 65, 80, 60, 40, 30].map((val, i) => (
              <div
                key={i}
                className="flex-1 bg-emerald-500/20 rounded-t-sm"
                style={{ height: `${val}%` }}
              />
            ))}
          </div>
        </div>

        {/* Timeline labels */}
        <div className="flex items-center justify-between text-[10px] text-muted border-t border-border/40 pt-1 font-mono">
          <span>06:00</span>
          <span>09:00</span>
          <span>12:00</span>
          <span>15:00</span>
          <span>18:00</span>
          <span>21:00</span>
          <span>24:00</span>
        </div>
      </Card>

      {/* Weather Forecast Card */}
      <Card className="p-4 bg-surface border border-border shadow-sm rounded-2xl flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground">Weather Forecast</span>
          <CloudSun className="w-4 h-4 text-muted" />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold text-foreground">27°</div>
            <div className="flex flex-col text-[11px] text-muted leading-tight">
              <span className="font-semibold text-foreground">Cloudy</span>
              <span>Feels like 29°</span>
            </div>
          </div>

          <div className="flex items-center gap-1 text-xs text-muted bg-surface-secondary px-2.5 py-1 rounded-lg border border-border cursor-pointer hover:text-foreground">
            <span>Conditions</span>
            <span className="text-[10px]">▼</span>
          </div>
        </div>

        {/* Temperature curve visual with icons */}
        <div className="h-14 w-full relative flex flex-col justify-end pt-2">
          {/* Amber temperature curve */}
          <svg className="w-full h-10 overflow-visible" preserveAspectRatio="none">
            <path
              d="M 10 32 Q 80 34, 150 12 T 290 28"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            {/* Area gradient under curve */}
            <path
              d="M 10 32 Q 80 34, 150 12 T 290 28 L 290 40 L 10 40 Z"
              fill="rgba(245, 158, 11, 0.15)"
            />
          </svg>
          <div className="flex items-center justify-between text-[11px] text-muted pt-1">
            <span>☁️ 25°</span>
            <span>⛅ 28°</span>
            <span>☀️ 32°</span>
            <span>⛅ 30°</span>
            <span>☁️ 27°</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
