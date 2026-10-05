"use client";

import { useState } from "react";
import { Button, Card, Chip, Separator } from "@heroui/react";
import {
  ArrowUp,
  ArrowDown,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  RotateCw,
  Hand,
  ShieldAlert,
  ShieldCheck,
  PlaneTakeoff,
  PlaneLanding,
  Home,
  OctagonAlert,
  Crosshair,
  Zap,
} from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface StepControllerProps {
  activeStepSize: number;
  onSetStepSize: (size: number) => void;
  onStep: (axis: string) => void;
  onCommand: (command: string, params?: Record<string, any>, confirm?: boolean) => void;
  armed: boolean;
  flightMode?: string;
}

const STEP_PRESETS = [
  { label: "1 cm", value: 0.01 },
  { label: "10 cm", value: 0.10 },
  { label: "1 ft", value: 0.3048 },
  { label: "1 m", value: 1.00 },
];

export default function StepController({
  activeStepSize,
  onSetStepSize,
  onStep,
  onCommand,
  armed,
}: StepControllerProps) {
  const [takeoffAlt, setTakeoffAlt] = useState<number>(1.5);

  const handleTakeoff = () => {
    onCommand("takeoff", { altitude: takeoffAlt });
  };

  const handleEmergencyKill = () => {
    if (confirm("⚠️ EMERGENCY MOTOR KILL: Motors will shut off instantly. Are you sure?")) {
      onCommand("kill", {}, true);
    }
  };

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-4 p-4">
        {/* Header and Step Selector */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
                <Crosshair className="w-3.5 h-3.5 text-accent" />
              </div>
              <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
                Precision Step Control
              </span>
            </div>
            <Chip size="sm" variant="soft" color="accent" className="font-mono text-[10px] font-bold">
              {activeStepSize < 0.3 ? `${(activeStepSize * 100).toFixed(0)} cm` : `${(activeStepSize / 0.3048).toFixed(0)} ft`}
            </Chip>
          </div>

          {/* Preset Selector */}
          <div className="grid grid-cols-4 gap-1.5 p-1.5 bg-surface-secondary rounded-lg border border-border">
            {STEP_PRESETS.map((p) => {
              const isSelected = Math.abs(activeStepSize - p.value) < 0.001;
              return (
                <Button
                  key={p.value}
                  size="sm"
                  variant={isSelected ? "primary" : "ghost"}
                  className="font-mono text-xs h-7 min-w-0"
                  onPress={() => onSetStepSize(p.value)}
                >
                  {p.label}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Stepper Keypads Layout */}
        <div className="grid grid-cols-3 gap-3 items-stretch">
          {/* Left: Altitude Stepper */}
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col items-center gap-2 p-2.5">
              <span className="text-[10px] font-mono font-semibold uppercase text-muted tracking-wider">
                Altitude
              </span>
              <GcsTooltip content="Climb by selected step">
                <Button
                  size="sm"
                  variant="primary"
                  className="w-full font-mono text-xs font-semibold"
                  onPress={() => onStep("up")}
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                  <span>Climb</span>
                </Button>
              </GcsTooltip>
              <GcsTooltip content="Descend by selected step">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full font-mono text-xs font-semibold"
                  onPress={() => onStep("down")}
                >
                  <ArrowDown className="w-3.5 h-3.5" />
                  <span>Descend</span>
                </Button>
              </GcsTooltip>
            </div>
          </Card>

          {/* Center: Planar Body NED Stepper */}
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col items-center gap-1.5 p-2">
              <span className="text-[10px] font-mono font-semibold uppercase text-muted tracking-wider">
                Body NED
              </span>

              <div className="grid grid-cols-3 gap-1.5 w-full">
                <div />
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 min-w-0 p-0"
                  aria-label="Step Forward"
                  onPress={() => onStep("forward")}
                >
                  <ChevronUp className="w-4 h-4 text-accent" />
                </Button>
                <div />

                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 min-w-0 p-0"
                  aria-label="Step Left"
                  onPress={() => onStep("left")}
                >
                  <ChevronLeft className="w-4 h-4 text-accent" />
                </Button>

                <GcsTooltip content="Hold position (Loiter)">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 min-w-0 p-0 border-amber-500/50 text-amber-500"
                    aria-label="Loiter / Hold Position"
                    onPress={() => onCommand("hold")}
                  >
                    <Hand className="w-3.5 h-3.5" />
                  </Button>
                </GcsTooltip>

                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 min-w-0 p-0"
                  aria-label="Step Right"
                  onPress={() => onStep("right")}
                >
                  <ChevronRight className="w-4 h-4 text-accent" />
                </Button>

                <div />
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 min-w-0 p-0"
                  aria-label="Step Backward"
                  onPress={() => onStep("backward")}
                >
                  <ChevronDown className="w-4 h-4 text-accent" />
                </Button>
                <div />
              </div>
            </div>
          </Card>

          {/* Right: Heading Yaw Stepper */}
          <Card className="bg-surface-secondary border border-border shadow-none">
            <div className="flex flex-col items-center gap-2 p-2.5">
              <span className="text-[10px] font-mono font-semibold uppercase text-muted tracking-wider">
                Heading
              </span>
              <GcsTooltip content="Rotate counterclockwise 15°">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full font-mono text-xs font-semibold"
                  onPress={() => onStep("yaw_left")}
                >
                  <RotateCcw className="w-3.5 h-3.5 text-accent" />
                  <span>-15°</span>
                </Button>
              </GcsTooltip>
              <GcsTooltip content="Rotate clockwise 15°">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full font-mono text-xs font-semibold"
                  onPress={() => onStep("yaw_right")}
                >
                  <RotateCw className="w-3.5 h-3.5 text-accent" />
                  <span>+15°</span>
                </Button>
              </GcsTooltip>
            </div>
          </Card>
        </div>

        {/* Flight Control Actions */}
        <div className="flex flex-col gap-3">
          <Separator className="bg-border" />
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase text-muted tracking-wider">
              Flight Authority
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {armed ? (
              <GcsTooltip content="Disarm motors — safe to approach">
                <Button
                  size="sm"
                  variant="outline"
                  className="font-mono text-xs font-bold text-amber-500 border-amber-500/50"
                  onPress={() => onCommand("disarm")}
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Disarm</span>
                </Button>
              </GcsTooltip>
            ) : (
              <GcsTooltip content="Arm motors — propellers will spin">
                <Button
                  size="sm"
                  variant="danger"
                  className="font-mono text-xs font-bold"
                  onPress={() => onCommand("arm")}
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>Arm Drone</span>
                </Button>
              </GcsTooltip>
            )}

            <GcsTooltip content={`Takeoff to ${takeoffAlt}m altitude`}>
              <Button
                size="sm"
                variant="primary"
                className="font-mono text-xs font-semibold"
                onPress={handleTakeoff}
              >
                <PlaneTakeoff className="w-4 h-4" />
                <span>Takeoff ({takeoffAlt}m)</span>
              </Button>
            </GcsTooltip>

            <GcsTooltip content="Land at current position">
              <Button
                size="sm"
                variant="outline"
                className="font-mono text-xs font-semibold"
                onPress={() => onCommand("land")}
              >
                <PlaneLanding className="w-4 h-4" />
                <span>Land Here</span>
              </Button>
            </GcsTooltip>

            <GcsTooltip content="Return to launch point">
              <Button
                size="sm"
                variant="outline"
                className="font-mono text-xs font-semibold text-amber-500 border-amber-500/50"
                onPress={() => onCommand("rtl")}
              >
                <Home className="w-4 h-4" />
                <span>RTL</span>
              </Button>
            </GcsTooltip>

            {!armed && (
              <GcsTooltip content="Direct bench arm override (bypasses pre-arm checks with magic 21196)">
                <Button
                  size="sm"
                  variant="outline"
                  className="font-mono text-[11px] font-bold text-danger border-danger/40 hover:bg-danger/10 col-span-2 h-7"
                  onPress={() => {
                    if (confirm("⚠️ FORCE ARM (BENCH TEST):\n\nEnsure all propellers are removed!\nBypasses pre-arm checks to test motors directly.")) {
                      onCommand("arm", { force: true }, true);
                    }
                  }}
                >
                  <Zap className="w-3 h-3" />
                  <span>Force Arm (Bench Override)</span>
                </Button>
              </GcsTooltip>
            )}
          </div>

          {/* Emergency Kill Switch */}
          <GcsTooltip content="EMERGENCY — Cuts all motor power instantly">
            <Button
              size="sm"
              variant="danger"
              className="w-full font-mono text-xs font-bold tracking-wider"
              onPress={handleEmergencyKill}
            >
              <OctagonAlert className="w-4 h-4" />
              <span>EMERGENCY MOTOR CUT</span>
            </Button>
          </GcsTooltip>
        </div>
      </div>
    </Card>
  );
}
