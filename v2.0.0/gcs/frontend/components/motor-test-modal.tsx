"use client";

import { useState } from "react";
import { Button, Card, Chip } from "@heroui/react";
import { Disc3, StopCircle, Zap, Shield, RotateCw, AlertTriangle, Battery, Cpu } from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface MotorTestProps {
  onTestMotor: (motor: number, throttle: number, duration: number) => void;
  onCommand?: (command: string, params?: Record<string, any>) => void;
  armed?: boolean;
}

const SPEED_PRESETS = [5, 10, 15, 20, 25, 30];
const DUR_PRESETS = [1, 2, 3, 5];

export default function MotorTestModal({ onTestMotor, onCommand }: MotorTestProps) {
  const [throttle, setThrottle] = useState<number>(15);
  const [duration, setDuration] = useState<number>(2);
  const [showChecklist, setShowChecklist] = useState<boolean>(true);

  const handleTest = (motorNum: number) => {
    onTestMotor(motorNum, throttle, duration);
  };

  const handleStopAll = () => {
    onTestMotor(1, 0, 0);
  };

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
              <Disc3 className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
              Motor Spin Test
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="ghost"
              className="text-[10px] font-mono text-muted h-6 px-1.5"
              onPress={() => setShowChecklist(!showChecklist)}
            >
              {showChecklist ? "Hide Tips" : "Hardware Tips"}
            </Button>
            <Chip size="sm" variant="soft" color="warning" className="font-mono text-[10px] font-bold">
              PROPS OFF
            </Chip>
          </div>
        </div>

        {/* Hardware Troubleshooting Checklist */}
        {showChecklist && (
          <div className="p-2.5 bg-warning/5 border border-warning/20 rounded-lg flex flex-col gap-1.5 text-[11px] font-mono">
            <div className="flex items-center gap-1.5 text-warning font-bold">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Motors not turning when commanded? Check:</span>
            </div>
            <ul className="text-muted list-disc list-inside space-y-0.5 text-[10px] pl-1">
              <li>
                <strong className="text-foreground">LiPo Battery:</strong> Main battery (11.1V/14.8V) must be connected to XT60. USB 5V <span className="text-danger font-semibold">cannot</span> spin motors.
              </li>
              <li>
                <strong className="text-foreground">Throttle:</strong> Try <span className="text-accent font-semibold">15% or 20%</span>. 10% is often inside uncalibrated ESC deadbands.
              </li>
              <li>
                <strong className="text-foreground">Wiring:</strong> ESCs must plug into <span className="text-foreground font-semibold">MAIN OUT 1-4</span> (not AUX). Signal wire (white/yellow) facing downwards/inside.
              </li>
              <li>
                <strong className="text-foreground">Safety Switch:</strong> Hold red button until solid red, or click Disengage below.
              </li>
            </ul>
          </div>
        )}

        {/* Throttle Controls */}
        <Card className="bg-surface-secondary border border-border shadow-none">
          <div className="flex flex-col gap-2.5 p-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted uppercase tracking-wider text-[10px]">Throttle Power</span>
              <span className="text-accent font-bold">{throttle}%</span>
            </div>

            <div className="flex items-center gap-1">
              {SPEED_PRESETS.map((val) => (
                <Button
                  key={val}
                  size="sm"
                  variant={throttle === val ? "primary" : "outline"}
                  className="flex-1 font-mono text-xs h-7 min-w-0 px-0"
                  onPress={() => setThrottle(val)}
                >
                  {val}%
                </Button>
              ))}
            </div>

            {/* Duration selector */}
            <div className="flex items-center justify-between text-xs font-mono pt-1">
              <span className="text-muted uppercase tracking-wider text-[10px]">Duration</span>
              <div className="flex items-center gap-1.5">
                {DUR_PRESETS.map((dur) => (
                  <Button
                    key={dur}
                    size="sm"
                    variant={duration === dur ? "primary" : "outline"}
                    className="font-mono text-xs h-6 min-w-0 px-2"
                    onPress={() => setDuration(dur)}
                  >
                    {dur}s
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Motor Action Buttons */}
        <div className="grid grid-cols-2 gap-2">
          {[
            { num: 1, label: "Motor 1 (FR)" },
            { num: 2, label: "Motor 2 (RL)" },
            { num: 3, label: "Motor 3 (FL)" },
            { num: 4, label: "Motor 4 (RR)" },
          ].map(({ num, label }) => (
            <GcsTooltip key={num} content={`Spin motor ${num} at ${throttle}% for ${duration}s`}>
              <Button
                size="sm"
                variant="outline"
                className="font-mono text-xs font-semibold"
                onPress={() => handleTest(num)}
              >
                <Disc3 className="w-3 h-3 text-accent" />
                {label}
              </Button>
            </GcsTooltip>
          ))}
        </div>

        {/* Quick Safety Disengage & Reboot Helper */}
        {onCommand && (
          <div className="flex items-center justify-between p-2 bg-surface-secondary rounded-lg border border-border text-[10px] font-mono gap-1">
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[10px] px-2 text-accent border-accent/40 hover:bg-accent/10 flex-1"
              onPress={() => onCommand("safety_off")}
            >
              <Shield className="w-3 h-3 mr-1 text-accent" />
              Disengage Safety
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[10px] px-2 text-muted border-border hover:text-foreground"
              onPress={() => onCommand("reboot")}
            >
              <RotateCw className="w-3 h-3 mr-1" />
              Reboot FC
            </Button>
          </div>
        )}

        <div className="flex items-center gap-2">
          <GcsTooltip content="Test all 4 motors in sequence">
            <Button
              size="sm"
              variant="primary"
              className="flex-1 font-mono text-xs font-bold"
              onPress={() => handleTest(0)}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Test Sequence (1→4)</span>
            </Button>
          </GcsTooltip>

          <GcsTooltip content="Emergency stop all motors">
            <Button
              size="sm"
              variant="danger"
              className="font-mono text-xs font-bold"
              onPress={handleStopAll}
            >
              <StopCircle className="w-4 h-4" />
              <span>STOP</span>
            </Button>
          </GcsTooltip>
        </div>
      </div>
    </Card>
  );
}
