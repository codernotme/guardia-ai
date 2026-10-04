"use client";

import { useState } from "react";
import { Button, Card, Chip, Separator } from "@heroui/react";
import { MapPin, Package, Send, Trash2, Navigation } from "lucide-react";
import { WaypointItem } from "@/types/telemetry";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface MissionPlannerProps {
  waypoints: WaypointItem[];
  onUploadMission: (waypoints: WaypointItem[]) => void;
  onClearMission: () => void;
  onDropPayload: () => void;
  droneLat?: number;
  droneLon?: number;
}

export default function MissionPlanner({
  waypoints,
  onUploadMission,
  onClearMission,
  onDropPayload,
}: MissionPlannerProps) {
  const [defaultAlt, setDefaultAlt] = useState<number>(10);
  const [defaultSpeed, setDefaultSpeed] = useState<number>(2.5);

  const handleDropPayload = () => {
    if (confirm("⚠️ PAYLOAD RELEASE: Confirm servo release of delivery payload?")) {
      onDropPayload();
    }
  };

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
              <Navigation className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
              Mission Planner
            </span>
          </div>
          <Chip size="sm" variant="soft" color={waypoints.length > 0 ? "accent" : "default"} className="font-mono text-[10px] font-bold">
            {waypoints.length} WP{waypoints.length !== 1 ? "S" : ""}
          </Chip>
        </div>

        {/* Waypoint Parameters */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col gap-1 p-2.5">
              <span className="text-[9px] text-muted uppercase tracking-wider">Cruise Alt</span>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  aria-label="Default Cruise Altitude"
                  value={defaultAlt}
                  onChange={(e) => setDefaultAlt(Number(e.target.value))}
                  className="w-14 bg-background border border-border rounded-md px-2 py-1 text-foreground text-xs font-bold focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
                />
                <span className="text-muted text-[10px]">m</span>
              </div>
            </div>
          </Card>

          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col gap-1 p-2.5">
              <span className="text-[9px] text-muted uppercase tracking-wider">WP Speed</span>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  aria-label="Waypoint Speed"
                  value={defaultSpeed}
                  onChange={(e) => setDefaultSpeed(Number(e.target.value))}
                  className="w-14 bg-background border border-border rounded-md px-2 py-1 text-foreground text-xs font-bold focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
                />
                <span className="text-muted text-[10px]">m/s</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Waypoint List / Queue */}
        <div className="flex flex-col gap-1 max-h-36 overflow-y-auto font-mono text-xs p-2 bg-background rounded-lg border border-border">
          {waypoints.length === 0 ? (
            <div className="p-4 text-center text-muted italic text-[11px] flex flex-col items-center gap-2">
              <MapPin className="w-5 h-5 text-muted/50" />
              <span>Click the tactical map to place waypoints</span>
            </div>
          ) : (
            waypoints.map((wp, idx) => (
              <Card
                key={wp.id}
                className="bg-surface-secondary border border-border shadow-none"
              >
                <div className="flex items-center justify-between p-2 text-[10px]">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-accent/20 text-accent flex items-center justify-center font-bold text-[10px]">
                      {idx + 1}
                    </span>
                    <span className="text-foreground tabular-nums">
                      {wp.lat.toFixed(5)}°, {wp.lon.toFixed(5)}°
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted">
                    <span>{wp.alt}m</span>
                    <span>{wp.speed}m/s</span>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <GcsTooltip content="Upload waypoint mission to Pixhawk flight controller">
            <Button
              size="sm"
              variant="primary"
              className="flex-1 font-mono text-xs font-bold"
              isDisabled={waypoints.length === 0}
              onPress={() => onUploadMission(waypoints)}
            >
              <Send className="w-3.5 h-3.5" />
              <span>Upload to Pixhawk</span>
            </Button>
          </GcsTooltip>

          <GcsTooltip content="Clear all waypoints">
            <Button
              size="sm"
              variant="outline"
              className="font-mono text-xs"
              isDisabled={waypoints.length === 0}
              onPress={onClearMission}
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </Button>
          </GcsTooltip>
        </div>

        <Separator className="bg-border" />

        {/* Guardia AI Delivery Service Trigger */}
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-[10px] font-mono font-bold text-foreground uppercase">
              Payload Servo
            </span>
            <span className="text-[9px] font-mono text-muted">AUX Ch7 Relay</span>
          </div>

          <GcsTooltip content="Release delivery payload via servo actuator">
            <Button
              size="sm"
              variant="outline"
              className="font-mono text-xs font-bold text-amber-500 border-amber-500/50"
              onPress={handleDropPayload}
            >
              <Package className="w-3.5 h-3.5" />
              <span>Release</span>
            </Button>
          </GcsTooltip>
        </div>
      </div>
    </Card>
  );
}
