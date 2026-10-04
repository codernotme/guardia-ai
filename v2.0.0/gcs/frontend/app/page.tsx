"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Card, Chip, Tabs } from "@heroui/react";
import { Map, Gauge, Split, Activity } from "lucide-react";

import { useTelemetry } from "@/hooks/use-telemetry";
import GcsHeader from "@/components/gcs-header";
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
    <div className="w-full h-full min-h-[480px] flex flex-col items-center justify-center bg-surface text-accent font-mono text-xs gap-3 rounded-lg border border-border">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      <span className="tracking-widest uppercase">Initializing Tactical GPS Map...</span>
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
  } = useTelemetry();

  const [activeCenterTab, setActiveCenterTab] = useState<string>("split");
  const [waypoints, setWaypoints] = useState<WaypointItem[]>([]);

  const handleAddWaypoint = (lat: number, lon: number) => {
    const newWp: WaypointItem = {
      id: `${Date.now()}-${waypoints.length + 1}`,
      lat,
      lon,
      alt: 10,
      speed: 2.5,
    };
    setWaypoints((prev) => [...prev, newWp]);
    sendCommand("nudge_badge", { msg: `Added Waypoint #${waypoints.length + 1} at ${lat.toFixed(5)}, ${lon.toFixed(5)}` });
  };

  const handleUploadMission = (wps: WaypointItem[]) => {
    sendCommand("upload_mission", { waypoints: wps, altitude: 10.0 });
  };

  const handleClearMission = () => {
    setWaypoints([]);
    sendCommand("clear_mission");
  };

  const handleDropPayload = () => {
    sendCommand("servo_trigger", { channel: 7, pwm: 1900, duration: 1.5 });
  };

  return (
    <div className="flex flex-col min-h-screen w-full bg-background text-foreground">
      {/* Top Tactical HUD Bar */}
      <GcsHeader telemetry={telemetry} connected={connected} />

      {/* Command Notification Toast Banner */}
      {lastCommand && (
        <div className="w-full bg-surface border-b border-border px-4 py-2 flex items-center justify-between font-mono text-xs animate-in fade-in slide-in-from-top-1 duration-300">
          <div className="flex items-center gap-2.5">
            <div className={`w-2 h-2 rounded-full ${lastCommand.ok ? "bg-success animate-pulse" : "bg-warning animate-pulse"}`} />
            <span className="text-muted uppercase tracking-wider text-[10px]">Status:</span>
            <span className={`font-bold ${lastCommand.ok ? "text-success" : "text-warning"}`}>
              {lastCommand.msg}
            </span>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-muted">
            <span className="flex items-center gap-1">
              <Activity className="w-3 h-3" />
              <span>5Hz</span>
            </span>
          </div>
        </div>
      )}

      {/* Main Tactical Grid Layout */}
      <main className="flex-1 w-full p-3 grid grid-cols-1 xl:grid-cols-12 gap-3 items-start">
        {/* Left Column: Flight Controls & Hardware Link (xl: 3 cols) */}
        <div className="xl:col-span-3 flex flex-col gap-3">
          {/* Step & Nudge Controller */}
          <StepController
            activeStepSize={activeStepSize}
            onSetStepSize={setActiveStepSize}
            onStep={sendStep}
            onCommand={sendCommand}
            armed={telemetry.armed}
            flightMode={telemetry.flight_mode}
          />

          {/* FlySky RC Channels & Serial Port Link */}
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

          {/* Bench Motor Spin Test */}
          <MotorTestModal onTestMotor={testMotor} armed={telemetry.armed} />
        </div>

        {/* Center Column: Visual Observation (Map & Primary Flight Display) (xl: 6 cols) */}
        <div className="xl:col-span-6 flex flex-col gap-3">
          {/* View Mode Selector - HeroUI Tabs */}
          <Card className="bg-surface border border-border shadow-sm">
            <div className="p-2 flex items-center justify-between">
              <Tabs
                selectedKey={activeCenterTab}
                onSelectionChange={(key) => setActiveCenterTab(String(key))}
                variant="secondary"
              >
                <Tabs.List className="gap-1 font-mono">
                  <Tabs.Tab id="map" className="px-3 py-1.5 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-md">
                    <Map className="w-3.5 h-3.5" />
                    <span>Map</span>
                  </Tabs.Tab>
                  <Tabs.Tab id="pfd" className="px-3 py-1.5 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-md">
                    <Gauge className="w-3.5 h-3.5" />
                    <span>HUD / PFD</span>
                  </Tabs.Tab>
                  <Tabs.Tab id="split" className="px-3 py-1.5 text-xs uppercase tracking-wider flex items-center gap-1.5 cursor-pointer rounded-md">
                    <Split className="w-3.5 h-3.5" />
                    <span>Dual Split</span>
                  </Tabs.Tab>
                </Tabs.List>
              </Tabs>

              <Chip size="sm" variant="soft" color="success" className="font-mono text-[10px]">
                GPS LIVE
              </Chip>
            </div>
          </Card>

          {/* Map & Flight Display Panels based on activeCenterTab */}
          {activeCenterTab === "map" && (
            <div className="w-full h-[620px]">
              <TacticalMap
                lat={telemetry.lat}
                lon={telemetry.lon}
                heading={telemetry.heading}
                alt={telemetry.alt}
                speed={telemetry.groundspeed}
                sats={telemetry.gps_sats}
                fix={telemetry.gps_fix}
                breadcrumbs={breadcrumbs}
                onAddWaypoint={handleAddWaypoint}
              />
            </div>
          )}

          {activeCenterTab === "pfd" && (
            <div className="w-full flex flex-col gap-3">
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
            <div className="flex flex-col gap-3">
              {/* Map View */}
              <div className="w-full h-[400px]">
                <TacticalMap
                  lat={telemetry.lat}
                  lon={telemetry.lon}
                  heading={telemetry.heading}
                  alt={telemetry.alt}
                  speed={telemetry.groundspeed}
                  sats={telemetry.gps_sats}
                  fix={telemetry.gps_fix}
                  breadcrumbs={breadcrumbs}
                  onAddWaypoint={handleAddWaypoint}
                />
              </div>

              {/* Primary Flight Display & Attitude */}
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
        </div>

        {/* Right Column: Mission Planner & Live Analytics (xl: 3 cols) */}
        <div className="xl:col-span-3 flex flex-col gap-3">
          {/* Live Telemetry Analytics Graphs */}
          <AnalyticsPanel telemetry={telemetry} history={history} />

          {/* Autonomous Waypoint Mission & Delivery Planner */}
          <MissionPlanner
            waypoints={waypoints}
            onUploadMission={handleUploadMission}
            onClearMission={handleClearMission}
            onDropPayload={handleDropPayload}
            droneLat={telemetry.lat}
            droneLon={telemetry.lon}
          />
        </div>

        {/* Full-Width Bottom Bar: Tactical Log Stream */}
        <div className="xl:col-span-12 w-full">
          <TacticalLogStream logs={logs} statustext={telemetry.statustext} />
        </div>
      </main>
    </div>
  );
}
