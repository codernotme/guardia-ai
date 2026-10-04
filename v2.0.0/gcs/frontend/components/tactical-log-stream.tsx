"use client";

import { Card, Chip } from "@heroui/react";
import { LogEntry } from "@/types/telemetry";
import { Terminal, ShieldAlert } from "lucide-react";

interface LogStreamProps {
  logs: LogEntry[];
  statustext: string;
}

export default function TacticalLogStream({ logs, statustext }: LogStreamProps) {
  return (
    <Card className="bg-surface border border-border shadow-md overflow-visible">
      <div className="flex flex-col gap-2 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent/10 flex items-center justify-center">
              <Terminal className="w-3.5 h-3.5 text-accent" />
            </div>
            <span className="text-xs font-mono font-bold tracking-wider text-foreground uppercase">
              Mission Log
            </span>
          </div>
          {statustext && (
            <div className="flex items-center gap-1.5 max-w-[50%] truncate">
              <Chip size="sm" variant="soft" color="warning" className="font-mono text-[10px] max-w-full">
                <span className="flex items-center gap-1 truncate">
                  <ShieldAlert className="w-3 h-3 shrink-0" />
                  <span className="truncate">{statustext}</span>
                </span>
              </Chip>
            </div>
          )}
        </div>

        <div className="w-full h-32 overflow-y-auto font-mono text-[11px] p-2.5 bg-background rounded-lg border border-border flex flex-col gap-1 select-text">
          {logs.length === 0 ? (
            <span className="text-muted italic text-[11px] flex items-center gap-2 p-2">
              <Terminal className="w-3.5 h-3.5 text-muted/50" />
              No mission log events recorded yet...
            </span>
          ) : (
            logs.map((log) => {
              const isWarn = log.level === "WARN";
              const isCrit = log.level === "CRIT";

              return (
                <div
                  key={log.id}
                  className={`flex items-start gap-2 leading-relaxed px-1.5 py-0.5 rounded transition-colors ${
                    isCrit
                      ? "bg-danger/10 text-danger"
                      : isWarn
                      ? "text-warning"
                      : "text-foreground/80"
                  }`}
                >
                  <span className="text-muted shrink-0 text-[10px] tabular-nums">[{log.timestamp}]</span>
                  <Chip
                    size="sm"
                    variant="soft"
                    color={isCrit ? "danger" : isWarn ? "warning" : "accent"}
                    className="h-4 text-[8px] font-bold shrink-0 min-w-[38px] justify-center"
                  >
                    {log.level}
                  </Chip>
                  <span className={`break-all ${isCrit ? "font-bold" : ""}`}>{log.message}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </Card>
  );
}
