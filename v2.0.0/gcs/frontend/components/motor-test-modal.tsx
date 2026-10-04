"use client";

import { useState } from "react";
import { Button, Card, Chip } from "@heroui/react";
import { Disc3, StopCircle, Zap } from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface MotorTestProps {
  onTestMotor: (motor: number, throttle: number, duration: number) => void;
  armed?: boolean;
}

const SPEED_PRESETS = [5, 10, 15, 20, 25];
const DUR_PRESETS = [1, 2, 3, 5];

export default function MotorTestModal({ onTestMotor }: MotorTestProps) {
  const [throttle, setThrottle] = useState<number>(10);
  const [duration, setDuration] = useState<number>(2);

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
          <Chip size="sm" variant="soft" color="warning" className="font-mono text-[10px] font-bold">
            PROPS OFF
          </Chip>
        </div>

        {/* Throttle Controls */}
        <Card className="bg-surface-secondary border border-border shadow-none">
          <div className="flex flex-col gap-2.5 p-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-muted uppercase tracking-wider text-[10px]">Throttle</span>
              <span className="text-accent font-bold">{throttle}%</span>
            </div>

            <div className="flex items-center gap-1.5">
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
