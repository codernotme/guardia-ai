"use client";

import React from "react";
import {
  LayoutGrid,
  CloudSun,
  Zap,
  Compass,
  Layers,
  Wrench,
  Radio,
  RotateCw,
  LineChart,
  Terminal,
  Settings,
  HelpCircle,
  Crosshair,
} from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

export type NavTabId =
  | "overview"
  | "weather"
  | "nudge"
  | "mission"
  | "sectors"
  | "ardupilot"
  | "rc"
  | "motor"
  | "analytics"
  | "logs";

interface SidebarNavProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  onOpenSettings?: () => void;
  onOpenAutoSetup?: () => void;
  armed: boolean;
}

export default function SidebarNav({
  activeTab,
  onSelectTab,
  onOpenSettings,
  onOpenAutoSetup,
  armed,
}: SidebarNavProps) {
  const navItems = [
    { id: "overview" as NavTabId, label: "Tactical Dashboard", icon: LayoutGrid },
    { id: "weather" as NavTabId, label: "Atmospheric & Weather", icon: CloudSun },
    { id: "nudge" as NavTabId, label: "Precision Step Nudge (1cm/1ft)", icon: Zap },
    { id: "mission" as NavTabId, label: "Survey & Waypoint Navigation", icon: Compass },
    { id: "sectors" as NavTabId, label: "Agricultural & Recon Sectors", icon: Layers },
    { id: "ardupilot" as NavTabId, label: "ArduPilot Auto-Setup & Parameters", icon: Wrench, highlight: true },
    { id: "rc" as NavTabId, label: "FlySky RC Transmitter Monitor", icon: Radio },
    { id: "motor" as NavTabId, label: "Bench Motor Spin Test", icon: RotateCw },
    { id: "analytics" as NavTabId, label: "Telemetry & Performance Curves", icon: LineChart },
    { id: "logs" as NavTabId, label: "MAVLink Tactical Stream", icon: Terminal },
  ];

  return (
    <aside className="w-14 sm:w-16 flex flex-col items-center justify-between py-4 bg-[#14171A] border-r border-[#262A30] text-gray-400 select-none z-30 shrink-0">
      {/* Top Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <button
          onClick={() => onSelectTab("overview")}
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20 hover:scale-105 active:scale-95 transition-transform"
          aria-label="Guardia AI Home"
        >
          <Crosshair className="w-5 h-5 text-white" />
        </button>

        {/* Navigation Items */}
        <nav className="flex flex-col items-center gap-1.5 w-full px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <GcsTooltip key={item.id} content={item.label}>
                <button
                  onClick={() => {
                    if (item.id === "ardupilot" && onOpenAutoSetup) {
                      onOpenAutoSetup();
                    } else {
                      onSelectTab(item.id);
                    }
                  }}
                  className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 relative group ${
                    isActive
                      ? "bg-white/10 text-white shadow-inner font-bold"
                      : "text-gray-400 hover:text-white hover:bg-white/5"
                  } ${item.highlight ? "text-emerald-400 hover:text-emerald-300" : ""}`}
                >
                  <Icon className={`w-5 h-5 transition-transform group-hover:scale-110 ${isActive ? "text-white" : ""}`} />
                  {isActive && (
                    <span className="absolute left-0 top-2 bottom-2 w-1 bg-emerald-500 rounded-r-full" />
                  )}
                  {item.id === "ardupilot" && (
                    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  )}
                </button>
              </GcsTooltip>
            );
          })}
        </nav>
      </div>

      {/* Bottom Auxiliary Actions */}
      <div className="flex flex-col items-center gap-2 w-full px-2">
        <GcsTooltip content="Documentation & Pixhawk Pinouts">
          <button
            onClick={() => window.open("https://ardupilot.org/copter/", "_blank")}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <HelpCircle className="w-5 h-5" />
          </button>
        </GcsTooltip>

        <GcsTooltip content="GCS Configuration">
          <button
            onClick={onOpenSettings}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Settings className="w-5 h-5" />
          </button>
        </GcsTooltip>
      </div>
    </aside>
  );
}
