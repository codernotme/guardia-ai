"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Card, Chip, Tabs, Button } from "@heroui/react";
import {
  Map,
  Gauge,
  Split,
  Activity,
  Zap,
  Sliders,
  Radio,
  Layers,
  Sparkles,
  X,
} from "lucide-react";

import { useTelemetry } from "@/hooks/use-telemetry";
import GcsHeader from "@/components/gcs-header";
import SidebarNav, { NavTabId } from "@/components/sidebar-nav";
import FieldMetricsPanel from "@/components/field-metrics-panel";
import ArduPilotSetupModal from "@/components/ardupilot-setup-modal";
import StepController from "@/components/step-controller";
import RcChannelMonitor from "@/components/rc-channel-monitor";
import PrimaryFlightDisplay from "@/components/primary-flight-display";
import AnalyticsPanel from "@/components/analytics-panel";
import MotorTestModal from "@/components/motor-test-modal";
import TacticalLogStream from "@/components/tactical-log-stream";
import MissionPlanner from "@/components/mission-planner";
import { WaypointItem } from "@/types/telemetry";

// Dynamic import for Leaflet map to disable SSR
const TacticalMap = dynamic(() => import("@/components/tactical-map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[580px] flex flex-col items-center justify-center bg-surface text-accent font-mono text-xs gap-3 rounded-3xl border border-border">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      <span className="tracking-widest uppercase">Initializing Satellite Recon Map...</span>
    </div>
  ),
});

export default function GcsDashboardPage() {
  const {
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
    runArduPilotAutoSetup,
    fetchArduPilotParams,
    setArduPilotParam,
    fetchPrearmCheck,
    generateSurveyWaypoints,
  } = useTelemetry();

  // Navigation and Modal States
  const [activeNavTab, setActiveNavTab] = useState<NavTabId>("overview");
  const [isAutoSetupOpen, setIsAutoSetupOpen] = useState<boolean>(false);
  const [activeCenterTab, setActiveCenterTab] = useState<string>("map");
  const [waypoints, setWaypoints] = useState<WaypointItem[]>([]);
  const [isAiInsightsModalOpen, setIsAiInsightsModalOpen] = useState<boolean>(false);

  // Active flyout drawer for specialized tools (nudge, rc, motor, etc.)
  const [activeDrawer, setActiveDrawer] = useState<NavTabId | null>(null);

  const handleNavSelect = (tab: NavTabId) => {
    setActiveNavTab(tab);
    if (tab === "ardupilot") {
      setIsAutoSetupOpen(true);
    } else if (["nudge", "rc", "motor", "mission", "analytics", "logs"].includes(tab)) {
      setActiveDrawer(tab);
    } else {
      setActiveDrawer(null);
    }
  };

  const handleAddWaypoint = (lat: number, lon: number) => {
    const newWp: WaypointItem = {
      id: `${Date.now()}-${waypoints.length + 1}`,
      lat,
      lon,
      alt: 10,
      speed: 2.5,
    };
    setWaypoints((prev) => [...prev, newWp]);
    sendCommand("nudge_badge", {
      msg: `Added Waypoint #${waypoints.length + 1} at ${lat.toFixed(5)}, ${lon.toFixed(5)}`,
    });
  };

  const handleUploadMission = (wps: WaypointItem[]) => {
    sendCommand("upload_mission", { waypoints: wps, altitude: 10.0 });
  };

  const handleClearMission = () => {
    setWaypoints([]);
    sendCommand("clear_mission");
  };

  const handleDropPayload = () => {
    sendCommand("drop_payload");
  };

  const handleToggleArm = () => {
    if (telemetry.armed) {
      sendCommand("disarm", {}, false);
    } else {
      sendCommand("arm", { force: true }, true);
    }
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* ─────────────────────────────────────────────────────────────
          1. Leftmost Slim Vertical Navigation Dock (matching reference)
         ───────────────────────────────────────────────────────────── */}
      <SidebarNav
        activeTab={activeNavTab}
        onSelectTab={handleNavSelect}
        onOpenAutoSetup={() => setIsAutoSetupOpen(true)}
        onOpenSettings={() => setActiveDrawer("rc")}
        armed={telemetry.armed}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Tactical HUD Bar */}
        <GcsHeader
          telemetry={telemetry}
          connected={connected}
          onOpenCalibration={() => setIsAutoSetupOpen(true)}
        />

        {/* Command Notification Toast Banner */}
        {lastCommand && (
          <div className="w-full bg-surface border-b border-border px-4 py-2 flex items-center justify-between font-mono text-xs animate-in fade-in slide-in-from-top-1 duration-300">
            <div className="flex items-center gap-2.5">
              <div
                className={`w-2 h-2 rounded-full ${
                  lastCommand.ok ? "bg-emerald-500 animate-pulse" : "bg-amber-500 animate-pulse"
                }`}
              />
              <span className="text-muted uppercase tracking-wider text-[10px]">Status:</span>
              <span className={`font-bold ${lastCommand.ok ? "text-emerald-500" : "text-amber-500"}`}>
                {lastCommand.msg}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[10px] text-muted">
              <span className="flex items-center gap-1">
                <Activity className="w-3 h-3" />
                <span>5Hz Telemetry</span>
              </span>
            </div>
          </div>
        )}

        {/* ─────────────────────────────────────────────────────────────
            2. Main Two-Column Tablet Layout (Inspector on Left, Map on Right)
           ───────────────────────────────────────────────────────────── */}
        <main className="flex-1 w-full p-3 sm:p-4 overflow-hidden grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 items-stretch">
          {/* Left Column: Field / Sector Metrics & Environmental Inspector (lg: 4 cols) */}
          <div className="lg:col-span-4 h-full overflow-y-auto pr-1 flex flex-col gap-3 custom-scrollbar">
            <FieldMetricsPanel
              telemetry={telemetry}
              onOpenAiInsights={() => setIsAiInsightsModalOpen(true)}
            />
          </div>

          {/* Right Column: Full-Scale Satellite Map & Tactical Cockpit (lg: 8 cols) */}
          <div className="lg:col-span-8 h-full flex flex-col gap-2 relative">
            {/* View Mode Selector Tabs */}
            <div className="flex items-center justify-between px-1">
              <Tabs
                selectedKey={activeCenterTab}
                onSelectionChange={(key) => setActiveCenterTab(String(key))}
                variant="secondary"
              >
                <Tabs.List className="gap-1 font-mono text-xs">
                  <Tabs.Tab
                    id="map"
                    className="px-3 py-1 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-lg"
                  >
                    <Map className="w-3.5 h-3.5" />
                    <span>Satellite Recon</span>
                  </Tabs.Tab>
                  <Tabs.Tab
                    id="pfd"
                    className="px-3 py-1 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-lg"
                  >
                    <Gauge className="w-3.5 h-3.5" />
                    <span>HUD / Horizon</span>
                  </Tabs.Tab>
                  <Tabs.Tab
                    id="split"
                    className="px-3 py-1 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-lg"
                  >
                    <Split className="w-3.5 h-3.5" />
                    <span>Dual Tactical</span>
                  </Tabs.Tab>
                </Tabs.List>
              </Tabs>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg"
                  onPress={() => setIsAutoSetupOpen(true)}
                >
                  <Sparkles className="w-3 h-3 mr-1" />
                  <span>ArduPilot Ready</span>
                </Button>
              </div>
            </div>

            {/* Map / Flight Display View */}
            <div className="flex-1 w-full h-[calc(100%-42px)] rounded-3xl overflow-hidden relative">
              {activeCenterTab === "map" && (
                <TacticalMap
                  lat={telemetry.lat}
                  lon={telemetry.lon}
                  heading={telemetry.heading}
                  alt={telemetry.alt}
                  speed={telemetry.groundspeed}
                  sats={telemetry.gps_sats}
                  fix={telemetry.gps_fix}
                  breadcrumbs={breadcrumbs}
                  armed={telemetry.armed}
                  onAddWaypoint={handleAddWaypoint}
                  onOpenAutoSetup={() => setIsAutoSetupOpen(true)}
                  onToggleArm={handleToggleArm}
                />
              )}

              {activeCenterTab === "pfd" && (
                <div className="w-full h-full p-2 bg-surface rounded-3xl border border-border flex flex-col justify-center">
                  <PrimaryFlightDisplay
                    pitch={telemetry.pitch}
                    roll={telemetry.roll}
                    yaw={telemetry.yaw}
                    heading={telemetry.heading}
                    alt={telemetry.alt}
                    speed={telemetry.groundspeed}
                  />
                </div>
              )}

              {activeCenterTab === "split" && (
                <div className="w-full h-full grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div className="h-full rounded-2xl overflow-hidden">
                    <TacticalMap
                      lat={telemetry.lat}
                      lon={telemetry.lon}
                      heading={telemetry.heading}
                      alt={telemetry.alt}
                      speed={telemetry.groundspeed}
                      sats={telemetry.gps_sats}
                      fix={telemetry.gps_fix}
                      breadcrumbs={breadcrumbs}
                      armed={telemetry.armed}
                      onAddWaypoint={handleAddWaypoint}
                      onOpenAutoSetup={() => setIsAutoSetupOpen(true)}
                      onToggleArm={handleToggleArm}
                    />
                  </div>
                  <div className="h-full p-2 bg-surface rounded-2xl border border-border flex flex-col justify-center">
                    <PrimaryFlightDisplay
                      pitch={telemetry.pitch}
                      roll={telemetry.roll}
                      yaw={telemetry.yaw}
                      heading={telemetry.heading}
                      alt={telemetry.alt}
                      speed={telemetry.groundspeed}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. Specialized Multifunctional Flyout Drawers
         ───────────────────────────────────────────────────────────── */}
      {activeDrawer && (
        <div className="fixed inset-y-0 right-0 z-50 w-96 max-w-full bg-surface border-l border-border shadow-2xl p-4 flex flex-col gap-3 animate-in slide-in-from-right duration-300">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-foreground uppercase tracking-wider font-mono">
                {activeDrawer === "nudge" && "Step & Nudge Flight Control"}
                {activeDrawer === "rc" && "FlySky RC & Hardware Bridge"}
                {activeDrawer === "motor" && "Bench Motor Spin Test"}
                {activeDrawer === "mission" && "Autonomous Survey Planner"}
                {activeDrawer === "analytics" && "Telemetry & Curve Analytics"}
                {activeDrawer === "logs" && "MAVLink Real-Time Stream"}
              </span>
            </div>
            <button
              onClick={() => setActiveDrawer(null)}
              className="text-muted hover:text-foreground p-1"
              aria-label="Close drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3">
            {activeDrawer === "nudge" && (
              <StepController
                activeStepSize={activeStepSize}
                onSetStepSize={setActiveStepSize}
                onStep={sendStep}
                onCommand={sendCommand}
                armed={telemetry.armed}
                flightMode={telemetry.flight_mode}
              />
            )}

            {activeDrawer === "rc" && (
              <RcChannelMonitor
                rcChannels={telemetry.rc_channels}
                flightMode={telemetry.flight_mode}
                isHardware={telemetry.is_hardware}
                port={telemetry.port}
                baud={telemetry.baud}
                ports={ports}
                onSetFlightMode={setFlightMode}
                onConnectSerial={connectSerial}
              />
            )}

            {activeDrawer === "motor" && (
              <MotorTestModal
                onTestMotor={testMotor}
                onCommand={sendCommand}
                armed={telemetry.armed}
              />
            )}

            {activeDrawer === "mission" && (
              <MissionPlanner
                waypoints={waypoints}
                onUploadMission={handleUploadMission}
                onClearMission={handleClearMission}
                onDropPayload={handleDropPayload}
                droneLat={telemetry.lat}
                droneLon={telemetry.lon}
              />
            )}

            {activeDrawer === "analytics" && (
              <AnalyticsPanel telemetry={telemetry} history={history} />
            )}

            {activeDrawer === "logs" && (
              <TacticalLogStream logs={logs} statustext={telemetry.statustext} />
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          4. ArduPilot Auto-Setup & Parameters Wizard Modal
         ───────────────────────────────────────────────────────────── */}
      <ArduPilotSetupModal
        isOpen={isAutoSetupOpen}
        onClose={() => setIsAutoSetupOpen(false)}
        onRunAutoSetup={runArduPilotAutoSetup}
        onFetchParams={fetchArduPilotParams}
        onSetParam={setArduPilotParam}
        onFetchPrearm={fetchPrearmCheck}
        onCommand={sendCommand}
        armed={telemetry.armed}
      />
    </div>
  );
}
