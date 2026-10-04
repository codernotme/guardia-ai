"use client";

import { useMemo } from "react";
import { Card, Chip } from "@heroui/react";
import { Compass, Gauge, Navigation } from "lucide-react";

interface PFDProps {
  pitch: number; // in radians or degrees (backend sends radians)
  roll: number;  // in radians or degrees
  yaw: number;   // in radians or degrees
  heading: number; // in degrees (0-360)
  alt: number;
  speed: number;
}

export default function PrimaryFlightDisplay({
  pitch,
  roll,
  yaw,
  heading,
  alt,
  speed,
}: PFDProps) {
  // Convert radians to degrees if values are within typical radian range (< 2*PI)
  const rollDeg = useMemo(() => {
    return Math.abs(roll) <= 6.3 ? roll * (180 / Math.PI) : roll;
  }, [roll]);

  const pitchDeg = useMemo(() => {
    return Math.abs(pitch) <= 6.3 ? pitch * (180 / Math.PI) : pitch;
  }, [pitch]);

  const headingDeg = useMemo(() => {
    const raw = heading || (Math.abs(yaw) <= 6.3 ? (yaw * (180 / Math.PI) + 360) % 360 : yaw);
    return Math.round((raw + 360) % 360);
  }, [heading, yaw]);

  // Cardinal direction label
  const cardinal = useMemo(() => {
    const val = headingDeg;
    if (val >= 337.5 || val < 22.5) return "N";
    if (val >= 22.5 && val < 67.5) return "NE";
    if (val >= 67.5 && val < 112.5) return "E";
    if (val >= 112.5 && val < 157.5) return "SE";
    if (val >= 157.5 && val < 202.5) return "S";
    if (val >= 202.5 && val < 247.5) return "SW";
    if (val >= 247.5 && val < 292.5) return "W";
    return "NW";
  }, [headingDeg]);

  // Pitch ladder vertical translation (clamp to prevent overflow)
  const pitchPixelOffset = Math.max(-120, Math.min(120, pitchDeg * 3.5));

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-3 p-4">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
              <Gauge className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
              Primary Flight Display
            </span>
          </div>
          <div className="flex items-center gap-2 font-mono text-xs">
            <Chip
              size="sm"
              variant="soft"
              color={Math.abs(rollDeg) > 25 ? "warning" : "default"}
              className="font-mono text-[10px]"
            >
              BANK: {rollDeg >= 0 ? `+${rollDeg.toFixed(1)}°` : `${rollDeg.toFixed(1)}°`}
            </Chip>
            <Chip
              size="sm"
              variant="soft"
              color={Math.abs(pitchDeg) > 20 ? "warning" : "default"}
              className="font-mono text-[10px]"
            >
              PITCH: {pitchDeg >= 0 ? `+${pitchDeg.toFixed(1)}°` : `${pitchDeg.toFixed(1)}°`}
            </Chip>
          </div>
        </div>

        {/* Main Artificial Horizon & Pitch Ladder */}
        <div className="relative w-full h-[260px] rounded-lg overflow-hidden border border-accent/20 bg-surface-secondary select-none">
          {/* Horizon Sky & Ground Rotating Disk */}
          <div
            className="absolute w-[200%] h-[200%] -left-[50%] -top-[50%] transition-transform duration-100 ease-linear pointer-events-none"
            style={{
              transform: `translateY(${pitchPixelOffset}px) rotate(${-rollDeg}deg)`,
            }}
          >
            {/* Sky (Upper Half) */}
            <div className="w-full h-1/2 bg-gradient-to-b from-[#0e2738] to-[#123952] border-b-2 border-accent/80" />
            {/* Ground (Lower Half) */}
            <div className="w-full h-1/2 bg-gradient-to-b from-[#1b1c1e] to-[#0f1011]" />

            {/* Pitch Ladder Rungs */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              {[-30, -20, -10, 0, 10, 20, 30].map((deg) => {
                if (deg === 0) return null; // Horizon line already rendered
                const isPositive = deg > 0;
                return (
                  <div
                    key={deg}
                    className="absolute flex items-center gap-2"
                    style={{ transform: `translateY(${-deg * 3.5}px)` }}
                  >
                    <span className="text-[9px] font-mono text-accent/80 font-bold">{Math.abs(deg)}</span>
                    <div
                      className={`w-16 h-[2px] ${
                        isPositive ? "bg-accent/90" : "border-b border-dashed border-accent/80"
                      }`}
                    />
                    <span className="text-[9px] font-mono text-accent/80 font-bold">{Math.abs(deg)}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Fixed Aircraft Reticle / Crosshair (Center) */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <svg width="120" height="40" viewBox="0 0 120 40" fill="none">
              {/* Left Wing Bar */}
              <path d="M10 20 H45 V28 H41 V24 H10 Z" fill="#ffb300" stroke="#000" strokeWidth="1" />
              {/* Center Pip */}
              <circle cx="60" cy="20" r="3.5" fill="#ffb300" stroke="#000" strokeWidth="1" />
              {/* Right Wing Bar */}
              <path d="M75 28 V20 H110 Z M75 28 H79 V24 H110 Z" fill="#ffb300" stroke="#000" strokeWidth="1" />
            </svg>
          </div>

          {/* Roll Angle Arc & Scale at Top */}
          <div className="absolute top-2 inset-x-0 flex flex-col items-center pointer-events-none">
            <div className="relative w-44 h-12">
              {/* Bank Marker Scale */}
              <svg viewBox="0 0 200 60" className="w-full h-full stroke-accent/60 fill-none">
                <path d="M 20 50 A 90 90 0 0 1 180 50" strokeWidth="1.5" />
                {/* Scale Ticks */}
                <line x1="100" y1="10" x2="100" y2="18" strokeWidth="2" stroke="#ffb300" />
                <line x1="80" y1="13" x2="83" y2="19" strokeWidth="1.5" />
                <line x1="60" y1="19" x2="65" y2="24" strokeWidth="1.5" />
                <line x1="40" y1="28" x2="47" y2="32" strokeWidth="1.5" />
                <line x1="120" y1="13" x2="117" y2="19" strokeWidth="1.5" />
                <line x1="140" y1="19" x2="135" y2="24" strokeWidth="1.5" />
                <line x1="160" y1="28" x2="153" y2="32" strokeWidth="1.5" />
              </svg>

              {/* Dynamic Roll Pointer Triangle */}
              <div
                className="absolute top-1 left-1/2 -translate-x-1/2 w-3 h-3 transition-transform duration-100 ease-linear origin-bottom"
                style={{ transform: `rotate(${rollDeg}deg)` }}
              >
                <div className="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[8px] border-t-amber-400 mx-auto" />
              </div>
            </div>
          </div>

          {/* Left Side Speed Tape Indicator */}
          <div className="absolute left-2 top-10 bottom-10 w-14 flex flex-col justify-between bg-background/85 backdrop-blur-sm border border-border rounded-lg p-2 font-mono text-[10px]">
            <span className="text-muted uppercase text-[8px] tracking-wider text-center">SPD</span>
            <div className="flex flex-col items-center">
              <span className="font-bold text-sm text-foreground">{speed.toFixed(1)}</span>
              <span className="text-[8px] text-muted">m/s</span>
            </div>
            <span className="text-muted text-[9px] text-center font-semibold">{(speed * 3.6).toFixed(0)}kph</span>
          </div>

          {/* Right Side Altitude Tape Indicator */}
          <div className="absolute right-2 top-10 bottom-10 w-14 flex flex-col justify-between bg-background/85 backdrop-blur-sm border border-border rounded-lg p-2 font-mono text-[10px]">
            <span className="text-muted uppercase text-[8px] tracking-wider text-center">ALT</span>
            <div className="flex flex-col items-center">
              <span className="font-bold text-sm text-accent">{alt.toFixed(1)}</span>
              <span className="text-[8px] text-muted">m</span>
            </div>
            <span className="text-muted text-[9px] text-center font-semibold">{(alt * 3.28084).toFixed(0)}ft</span>
          </div>
        </div>

        {/* 360° Tactical Satellite Compass Ribbon & Rose */}
        <Card className="bg-surface-secondary border border-border shadow-none">
          <div className="flex flex-col gap-2 p-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2 text-accent">
                <Compass className="w-4 h-4" />
                <span className="font-bold tracking-wider">MAG/GPS HEADING</span>
              </div>
              <Chip size="sm" variant="soft" color="accent" className="font-mono text-[11px] font-bold">
                {headingDeg.toString().padStart(3, "0")}° {cardinal}
              </Chip>
            </div>

            {/* Horizontal Moving Compass Ribbon */}
            <div className="relative w-full h-9 bg-background rounded-lg border border-accent/30 overflow-hidden select-none">
              {/* Center Marker Line (Aircraft Heading Index) */}
              <div className="absolute left-1/2 top-0 bottom-0 w-[2px] bg-amber-400 -translate-x-1/2 z-20 pointer-events-none" />
              <div className="absolute left-1/2 top-0 -translate-x-1/2 w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[5px] border-t-amber-400 z-20" />

              {/* Moving Degree Scale */}
              <div
                className="absolute top-0 bottom-0 flex items-center transition-transform duration-100 ease-linear"
                style={{
                  // 1 degree = 4px translation
                  transform: `translateX(calc(50% - ${headingDeg * 4}px))`,
                }}
              >
                {/* Render 0 to 720 degrees to allow seamless wrap */}
                {Array.from({ length: 73 }).map((_, i) => {
                  const deg = (i * 10) % 360;
                  let label = `${deg}`;
                  let isSpecial = false;
                  if (deg === 0) {
                    label = "N";
                    isSpecial = true;
                  } else if (deg === 90) {
                    label = "E";
                    isSpecial = true;
                  } else if (deg === 180) {
                    label = "S";
                    isSpecial = true;
                  } else if (deg === 270) {
                    label = "W";
                    isSpecial = true;
                  }

                  return (
                    <div
                      key={i}
                      className="flex flex-col items-center justify-between h-full"
                      style={{ width: "40px", flexShrink: 0 }}
                    >
                      <span
                        className={`text-[9px] font-mono font-bold leading-none mt-1 ${
                          isSpecial ? (label === "N" ? "text-danger font-black" : "text-accent font-black") : "text-muted"
                        }`}
                      >
                        {label}
                      </span>
                      <div
                        className={`w-[1px] ${
                          isSpecial ? "h-3 bg-accent" : i % 3 === 0 ? "h-2.5 bg-muted" : "h-1.5 bg-muted/40"
                        }`}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </Card>
  );
}
