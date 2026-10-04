"use client";

import { useState } from "react";
import { Button, Card, Chip, Separator } from "@heroui/react";
import { Radio, RefreshCw, Usb, Loader2 } from "lucide-react";
import { SerialPortInfo } from "@/types/telemetry";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface RcMonitorProps {
  rcChannels: number[];
  flightMode: string;
  isHardware: boolean;
  port: string;
  baud: number;
  ports: SerialPortInfo[];
  onSetFlightMode: (mode: string) => void;
  onConnectSerial: (port: string, baud: number) => void;
}

const RC_CHANNEL_NAMES = [
  "CH1: Roll (Ail)",
  "CH2: Pitch (Ele)",
  "CH3: Throttle",
  "CH4: Yaw (Rud)",
  "CH5: Mode Switch",
  "CH6: Arm Switch",
  "CH7: Aux 1",
  "CH8: Aux 2",
];

const FLIGHT_MODES = ["STABILIZE", "ALT_HOLD", "LOITER", "GUIDED", "RTL", "LAND"];

export default function RcChannelMonitor({
  rcChannels,
  flightMode,
  isHardware,
  port,
  baud,
  ports,
  onSetFlightMode,
  onConnectSerial,
}: RcMonitorProps) {
  const [selectedPort, setSelectedPort] = useState<string>("AUTO");
  const [selectedBaud, setSelectedBaud] = useState<number>(115200);
  const [connecting, setConnecting] = useState<boolean>(false);

  const handleConnect = async () => {
    setConnecting(true);
    await onConnectSerial(selectedPort, selectedBaud);
    setConnecting(false);
  };

  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-4 p-4">
        {/* Hardware Link Configuration */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
                <Usb className="w-3.5 h-3.5 text-accent" />
              </div>
              <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
                Pixhawk 2.4.8 Link
              </span>
            </div>
            <Chip
              size="sm"
              variant="soft"
              color={isHardware ? "success" : "default"}
              className="font-mono text-[10px]"
            >
              {isHardware ? `${port} @ ${baud}` : "SIMULATED"}
            </Chip>
          </div>

          <div className="grid grid-cols-5 gap-2 items-center">
            <div className="col-span-2">
              <select
                aria-label="Serial Port"
                value={selectedPort}
                onChange={(e) => setSelectedPort(e.target.value)}
                className="w-full bg-surface-secondary border border-border rounded-lg px-2.5 py-2 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
              >
                <option value="AUTO">AUTO-DETECT</option>
                {ports.map((p) => (
                  <option key={p.device} value={p.device}>
                    {p.device} ({p.description.substring(0, 16)})
                  </option>
                ))}
                <option value="COM5">COM5 (Pixhawk USB)</option>
                <option value="COM4">COM4 (HC-05 BT)</option>
                <option value="COM3">COM3 (Serial SPP)</option>
              </select>
            </div>

            <div className="col-span-2">
              <select
                aria-label="Baud Rate"
                value={selectedBaud}
                onChange={(e) => setSelectedBaud(Number(e.target.value))}
                className="w-full bg-surface-secondary border border-border rounded-lg px-2.5 py-2 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent transition-colors"
              >
                <option value={115200}>115200 (USB)</option>
                <option value={57600}>57600 (HC-05)</option>
                <option value={9600}>9600 (Legacy)</option>
              </select>
            </div>

            <GcsTooltip content="Establish serial connection">
              <Button
                size="sm"
                variant="primary"
                className="font-mono text-xs font-semibold col-span-1 min-w-0"
                onPress={handleConnect}
                isDisabled={connecting}
              >
                {connecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                <span>Link</span>
              </Button>
            </GcsTooltip>
          </div>
        </div>

        <Separator className="bg-border" />

        {/* Control Authority & Mode Selector */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase text-muted tracking-wider">
              Flight Mode
            </span>
            <Chip
              size="sm"
              variant="soft"
              color={flightMode === "GUIDED" ? "accent" : "warning"}
              className="font-mono text-[10px] font-bold"
            >
              {flightMode === "GUIDED" ? "GCS GUIDED" : `RC: ${flightMode}`}
            </Chip>
          </div>

          <div className="grid grid-cols-3 gap-1.5">
            {FLIGHT_MODES.map((mode) => {
              const isActive = flightMode === mode;
              return (
                <Button
                  key={mode}
                  size="sm"
                  variant={isActive ? "primary" : "outline"}
                  className="font-mono text-[11px] font-semibold h-7"
                  onPress={() => onSetFlightMode(mode)}
                >
                  {mode}
                </Button>
              );
            })}
          </div>
        </div>

        <Separator className="bg-border" />

        {/* FlySky RC 8-Channel Live Bar Monitor */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-accent animate-pulse" />
              <span className="text-[10px] font-mono uppercase text-muted tracking-wider">
                RC PWM Channels
              </span>
            </div>
            <span className="text-[9px] font-mono text-muted">8 CH • 1000–2000 µs</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {Array.from({ length: 8 }).map((_, idx) => {
              const pwm = rcChannels && rcChannels[idx] ? rcChannels[idx] : 1500;
              const pct = Math.max(0, Math.min(100, ((pwm - 1000) / 1000) * 100));
              const isCenter = Math.abs(pwm - 1500) < 30;

              return (
                <GcsTooltip key={idx} content={`${RC_CHANNEL_NAMES[idx]} — ${pwm} µs (${pct.toFixed(0)}%)`}>
                  <Card className="bg-surface-secondary border border-border shadow-none cursor-help hover:border-accent/30 transition-colors">
                    <div className="flex flex-col gap-1 p-2">
                      <div className="flex items-center justify-between text-[9px] font-mono">
                        <span className="text-muted truncate">{RC_CHANNEL_NAMES[idx] || `CH${idx + 1}`}</span>
                        <span
                          className={`font-bold tabular-nums ${
                            isCenter ? "text-accent" : pwm > 1600 ? "text-success" : "text-warning"
                          }`}
                        >
                          {pwm}
                        </span>
                      </div>
                      <div className="relative w-full h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all duration-100"
                          style={{ width: `${pct}%` }}
                        />
                        {/* Center mark */}
                        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-muted/40" />
                      </div>
                    </div>
                  </Card>
                </GcsTooltip>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}
