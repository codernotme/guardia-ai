"use client";

import { useState } from "react";
import { Button, Card, Chip, Separator } from "@heroui/react";
import {
  Compass,
  Gauge,
  Sliders,
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Zap,
  X,
  Wrench,
  Loader2,
} from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface CalibrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCommand: (command: string, params?: Record<string, any>, confirm?: boolean) => void;
  armed: boolean;
  statustext: string;
}

export default function CalibrationModal({
  isOpen,
  onClose,
  onCommand,
  armed,
  statustext,
}: CalibrationModalProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<{ ok: boolean; msg: string } | null>(null);

  if (!isOpen) return null;

  const runAction = async (action: string, cmd: string, params: Record<string, any> = {}) => {
    setBusyAction(action);
    setActionResult(null);
    try {
      onCommand(cmd, params);
      setActionResult({ ok: true, msg: `Command ${cmd.toUpperCase()} dispatched` });
    } catch (e: any) {
      setActionResult({ ok: false, msg: e.message || "Failed to execute" });
    } finally {
      setTimeout(() => setBusyAction(null), 1200);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-2xl bg-surface border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface-secondary/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center text-accent">
              <Wrench className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="font-mono text-sm font-bold text-foreground">
                Sensor Calibration & Safety Configuration
              </span>
              <span className="text-[11px] font-mono text-muted">
                Pixhawk 2.4.8 Pre-Arm & Sensor Hardware Tuning
              </span>
            </div>
          </div>
          <Button
            size="sm"
            variant="ghost"
            isIconOnly
            onPress={onClose}
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content body */}
        <div className="p-4 overflow-y-auto flex flex-col gap-4 font-mono text-xs">
          {/* Quick Bench Mode Card */}
          <Card className="bg-accent/5 border border-accent/30 p-3.5 flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-accent" />
                <span className="font-bold text-accent uppercase tracking-wider text-[11px]">
                  Desk & Bench Test Mode (One-Click)
                </span>
              </div>
              <Chip size="sm" variant="soft" color="accent" className="text-[10px]">
                Recommended for Indoors
              </Chip>
            </div>
            <p className="text-[11px] text-muted leading-relaxed">
              Disables the physical safety switch check (<code className="text-accent">BRD_SAFETYENABLE=0</code>) and relaxes strict pre-arm checks (<code className="text-accent">ARMING_CHECK=0</code>). Allows immediate bench motor testing and indoor step controls without waiting for outdoor GPS 3D fix or compass clearance.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Button
                size="sm"
                variant="primary"
                className="font-bold text-xs"
                isDisabled={busyAction !== null}
                onPress={() => runAction("bench_mode", "bench_mode", { enable: true })}
              >
                {busyAction === "bench_mode" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                )}
                <span>Enable Bench Mode (Bypass Checks)</span>
              </Button>

              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                isDisabled={busyAction !== null}
                onPress={() => runAction("flight_mode", "bench_mode", { enable: false })}
              >
                <span>Restore Flight Mode (Strict Checks)</span>
              </Button>
            </div>
          </Card>

          {/* Safety Switch Control */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] uppercase text-muted tracking-wider font-bold">
              1. Hardware Safety Switch
            </span>
            <div className="grid grid-cols-2 gap-2">
              <Card className="p-3 bg-surface-secondary border border-border flex flex-col gap-2">
                <div className="flex items-center gap-1.5 text-danger font-bold text-[11px]">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Disengage Safety (Motors Live)</span>
                </div>
                <p className="text-[10px] text-muted leading-relaxed">
                  Sends software disengage command to Pixhawk (<code className="text-foreground">MAV_CMD_DO_SET_SAFETY_SWITCH, param1=0</code>). Required for motor tests if safety switch is active.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full text-danger border-danger/40 hover:bg-danger/10 font-bold"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("safety_off", "safety_off")}
                >
                  {busyAction === "safety_off" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Disengage Safety Switch</span>
                </Button>
              </Card>

              <Card className="p-3 bg-surface-secondary border border-border flex flex-col gap-2">
                <div className="flex items-center gap-1.5 text-success font-bold text-[11px]">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Engage Safety (Safe Mode)</span>
                </div>
                <p className="text-[10px] text-muted leading-relaxed">
                  Enables safety switch (<code className="text-foreground">param1=1</code>). Cuts ESC throttle signals to prevent accidental motor spin while handling.
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full text-success border-success/40 hover:bg-success/10"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("safety_on", "safety_on")}
                >
                  {busyAction === "safety_on" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Engage Safety Switch</span>
                </Button>
              </Card>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Sensor Calibrations */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] uppercase text-muted tracking-wider font-bold">
              2. Sensor Calibrations
            </span>
            <div className="grid grid-cols-2 gap-2">
              {/* Level Horizon Trim */}
              <Card className="p-3 bg-surface-secondary border border-border flex flex-col justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <Sliders className="w-3.5 h-3.5 text-accent" />
                    <span>Calibrate Level Horizon</span>
                  </div>
                  <p className="text-[10px] text-muted leading-relaxed">
                    Place drone on a flat, level surface. Calibrates accelerometer AHRS trim so pitch and roll read exactly 0.0°.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="primary"
                  className="w-full font-bold"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("cal_level", "calibrate_level")}
                >
                  {busyAction === "cal_level" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Calibrate Level (AHRS Trim)</span>
                </Button>
              </Card>

              {/* Gyroscope Calibration */}
              <Card className="p-3 bg-surface-secondary border border-border flex flex-col justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <RotateCw className="w-3.5 h-3.5 text-accent" />
                    <span>Calibrate Gyroscopes</span>
                  </div>
                  <p className="text-[10px] text-muted leading-relaxed">
                    Zeroes rate gyro drift. Keep the drone completely still on the table for 3 seconds during calibration.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full font-bold"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("cal_gyros", "calibrate_gyros")}
                >
                  {busyAction === "cal_gyros" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Calibrate Gyros</span>
                </Button>
              </Card>

              {/* Barometer Ground Reference */}
              <Card className="p-3 bg-surface-secondary border border-border flex flex-col justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <Gauge className="w-3.5 h-3.5 text-accent" />
                    <span>Zero Barometer (Ground Alt)</span>
                  </div>
                  <p className="text-[10px] text-muted leading-relaxed">
                    Measures current atmospheric pressure and sets relative altitude baseline to 0.0 meters.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("cal_baro", "calibrate_baro")}
                >
                  {busyAction === "cal_baro" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Zero Barometer Alt</span>
                </Button>
              </Card>

              {/* Compass Calibration */}
              <Card className="p-3 bg-surface-secondary border border-border flex flex-col justify-between gap-2">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <Compass className="w-3.5 h-3.5 text-accent" />
                    <span>Compass Magnetometer</span>
                  </div>
                  <p className="text-[10px] text-muted leading-relaxed">
                    Starts internal mag calibration. Rotate drone smoothly across all 3 axes away from metal desks.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  isDisabled={busyAction !== null}
                  onPress={() => runAction("cal_compass", "calibrate_compass")}
                >
                  {busyAction === "cal_compass" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>Start Compass Cal</span>
                </Button>
              </Card>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Force Arm (Bench Test) */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] uppercase text-muted tracking-wider font-bold">
              3. Bench Arming Override
            </span>
            <Card className="p-3 bg-danger/5 border border-danger/20 flex flex-col gap-2.5">
              <div className="flex items-center gap-2 text-danger font-bold text-[11px]">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Force Arm Drone (Bypass Pre-Arm Lock)</span>
              </div>
              <p className="text-[10px] text-muted leading-relaxed">
                Sends ArduPilot's magic bypass code (<code className="text-foreground">param2=21196</code>) to arm motors directly on the bench even when compass, GPS, or battery warnings are active.
                <span className="text-danger font-bold block mt-1">⚠️ ENSURE ALL PROPELLERS ARE REMOVED BEFORE ARMING ON THE BENCH!</span>
              </p>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="danger"
                  className="font-bold text-xs"
                  isDisabled={busyAction !== null || armed}
                  onPress={() => {
                    if (confirm("⚠️ FORCE ARM CONFIRMATION:\n\nAre all propellers removed from the drone?\nMotors may spin upon arming.")) {
                      runAction("force_arm", "arm", { force: true });
                    }
                  }}
                >
                  {busyAction === "force_arm" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>FORCE ARM MOTORS (Bench Test)</span>
                </Button>

                {armed && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-amber-500 border-amber-500/50 font-bold"
                    onPress={() => runAction("disarm", "disarm")}
                  >
                    <span>Disarm Drone</span>
                  </Button>
                )}
              </div>
            </Card>
          </div>

          {/* Live Flight Controller Status Feedback */}
          {statustext && (
            <div className="p-2.5 bg-background rounded-lg border border-border text-[11px] flex items-center gap-2">
              <span className="text-muted shrink-0 uppercase tracking-wider text-[9px]">FC Message:</span>
              <span className="font-bold text-accent truncate">{statustext}</span>
            </div>
          )}

          {actionResult && (
            <div
              className={`p-2.5 rounded-lg border text-[11px] ${
                actionResult.ok
                  ? "bg-success/10 border-success/30 text-success"
                  : "bg-danger/10 border-danger/30 text-danger"
              }`}
            >
              {actionResult.msg}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-border bg-surface-secondary/50 flex items-center justify-between">
          <Button
            size="sm"
            variant="outline"
            className="text-xs text-muted border-border hover:text-foreground"
            isDisabled={busyAction !== null}
            onPress={() => runAction("reboot", "reboot")}
          >
            {busyAction === "reboot" ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <RotateCw className="w-3.5 h-3.5 mr-1" />}
            <span>Reboot Autopilot</span>
          </Button>

          <Button size="sm" variant="primary" onPress={onClose}>
            Done
          </Button>
        </div>
      </Card>
    </div>
  );
}
