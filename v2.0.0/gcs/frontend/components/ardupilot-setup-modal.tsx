"use client";

import React, { useState, useEffect } from "react";
import {
  Button,
  Card,
  Chip,
  Tabs,
} from "@heroui/react";
import {
  Wrench,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  RotateCw,
  Sliders,
  ShieldCheck,
  Search,
  RefreshCw,
  Loader2,
  X,
} from "lucide-react";
import { ArduPilotParam, PrearmReport, AutoSetupStep } from "@/types/telemetry";

interface ArduPilotSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunAutoSetup: (profile: "bench" | "field", calibrateSensors: boolean) => Promise<any>;
  onFetchParams: () => Promise<ArduPilotParam[]>;
  onSetParam: (name: string, value: number) => Promise<boolean>;
  onFetchPrearm: () => Promise<PrearmReport | null>;
  onCommand: (command: string, params?: Record<string, any>) => void;
  armed: boolean;
}

export default function ArduPilotSetupModal({
  isOpen,
  onClose,
  onRunAutoSetup,
  onFetchParams,
  onSetParam,
  onFetchPrearm,
  onCommand,
  armed,
}: ArduPilotSetupModalProps) {
  const [activeTab, setActiveTab] = useState<string>("auto-setup");
  const [profile, setProfile] = useState<"bench" | "field">("bench");
  const [calibrateSensors, setCalibrateSensors] = useState<boolean>(true);
  const [isRunningSetup, setIsRunningSetup] = useState<boolean>(false);
  const [setupSteps, setSetupSteps] = useState<AutoSetupStep[]>([]);
  const [setupResultMsg, setSetupResultMsg] = useState<string | null>(null);

  // Pre-arm state
  const [prearmReport, setPrearmReport] = useState<PrearmReport | null>(null);
  const [isLoadingPrearm, setIsLoadingPrearm] = useState<boolean>(false);

  // Parameters state
  const [paramsList, setParamsList] = useState<ArduPilotParam[]>([]);
  const [paramSearch, setParamSearch] = useState<string>("");
  const [editingParam, setEditingParam] = useState<{ name: string; value: number } | null>(null);
  const [isWritingParam, setIsWritingParam] = useState<boolean>(false);

  // Load prearm and params on modal open
  useEffect(() => {
    if (isOpen) {
      loadPrearm();
      loadParams();
    }
  }, [isOpen]);

  const loadPrearm = async () => {
    setIsLoadingPrearm(true);
    const rep = await onFetchPrearm();
    setPrearmReport(rep);
    setIsLoadingPrearm(false);
  };

  const loadParams = async () => {
    const list = await onFetchParams();
    setParamsList(list);
  };

  const handleExecuteAutoSetup = async () => {
    setIsRunningSetup(true);
    setSetupResultMsg(null);
    setSetupSteps([]);

    const res = await onRunAutoSetup(profile, calibrateSensors);
    if (res && res.data && res.data.steps) {
      setSetupSteps(res.data.steps);
      setSetupResultMsg(res.msg);
    } else {
      setSetupResultMsg(res?.msg || "Auto-Setup finished with default configuration");
    }
    setIsRunningSetup(false);
    loadPrearm();
    loadParams();
  };

  const handleWriteParam = async (name: string, value: number) => {
    setIsWritingParam(true);
    const ok = await onSetParam(name, value);
    if (ok) {
      setEditingParam(null);
      loadParams();
    }
    setIsWritingParam(false);
  };

  if (!isOpen) return null;

  const filteredParams = paramsList.filter(
    (p) =>
      p.name.toLowerCase().includes(paramSearch.toLowerCase()) ||
      p.description.toLowerCase().includes(paramSearch.toLowerCase()) ||
      p.category.toLowerCase().includes(paramSearch.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <Card className="w-full max-w-3xl bg-surface border border-border shadow-2xl overflow-hidden max-h-[90vh] flex flex-col rounded-3xl p-6 font-sans">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <Wrench className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <h2 className="text-lg font-bold text-foreground tracking-tight">
                ArduPilot Auto-Setup & Flight Controller Manager
              </h2>
              <p className="text-xs text-muted">
                Pixhawk 2.4.8 · Copter Firmware · Zero-Telemetry Local Link
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Chip
              size="sm"
              variant="soft"
              color={armed ? "danger" : "success"}
              className="font-mono text-xs font-semibold"
            >
              {armed ? "ARMED — CAUTION" : "DISARMED (SAFE)"}
            </Chip>

            <button
              onClick={onClose}
              className="text-muted hover:text-foreground transition-colors p-1"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* HeroUI Tabs */}
        <Tabs
          selectedKey={activeTab}
          onSelectionChange={(key) => setActiveTab(String(key))}
          className="mb-4"
        >
          <Tabs.List className="gap-2 font-medium">
            <Tabs.Tab id="auto-setup" className="text-xs flex items-center gap-1.5 cursor-pointer">
              <Play className="w-3.5 h-3.5 text-emerald-500" />
              <span>1-Click Auto-Setup</span>
            </Tabs.Tab>
            <Tabs.Tab id="prearm" className="text-xs flex items-center gap-1.5 cursor-pointer">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
              <span>Pre-Arm Readiness</span>
            </Tabs.Tab>
            <Tabs.Tab id="params" className="text-xs flex items-center gap-1.5 cursor-pointer">
              <Sliders className="w-3.5 h-3.5 text-emerald-500" />
              <span>Parameter Catalog</span>
            </Tabs.Tab>
            <Tabs.Tab id="calibration" className="text-xs flex items-center gap-1.5 cursor-pointer">
              <RotateCw className="w-3.5 h-3.5 text-emerald-500" />
              <span>Sensors & Zeroing</span>
            </Tabs.Tab>
          </Tabs.List>
        </Tabs>

        {/* Content body with overflow */}
        <div className="flex-1 overflow-y-auto pr-1">
          {/* Tab 1: 1-Click Auto Setup */}
          {activeTab === "auto-setup" && (
            <div className="flex flex-col gap-4">
              <Card className="p-4 bg-surface-secondary border border-border rounded-2xl flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-foreground">Operational Profile</span>
                    <span className="text-xs text-muted">
                      Choose tuning presets for your current operational environment.
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant={profile === "bench" ? "primary" : "ghost"}
                      className={`text-xs font-semibold rounded-xl ${
                        profile === "bench"
                          ? "bg-emerald-500 text-white"
                          : "bg-surface border border-border text-foreground"
                      }`}
                      onPress={() => setProfile("bench")}
                    >
                      Bench Test Mode (Desk)
                    </Button>
                    <Button
                      size="sm"
                      variant={profile === "field" ? "primary" : "ghost"}
                      className={`text-xs font-semibold rounded-xl ${
                        profile === "field"
                          ? "bg-emerald-500 text-white"
                          : "bg-surface border border-border text-foreground"
                      }`}
                      onPress={() => setProfile("field")}
                    >
                      Outdoor Flight Mode
                    </Button>
                  </div>
                </div>

                <div className="p-3 bg-surface rounded-xl border border-border text-xs text-muted flex flex-col gap-1.5">
                  <div className="flex items-center gap-2 text-foreground font-semibold">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>
                      {profile === "bench"
                        ? "Bench Preset: Safety Bypass & Motor Diagnostics"
                        : "Flight Preset: Full Pre-arm Sanity & RTL Failsafes"}
                    </span>
                  </div>
                  <p>
                    {profile === "bench"
                      ? "Bypasses ARMING_CHECK and BRD_SAFETYENABLE for smooth indoor testing without props. Configures safe idle throttle (7%) and initializes analog battery sensors."
                      : "Enables all ArduPilot pre-arm safety checks (ARMING_CHECK=1), requires physical safety switch (BRD_SAFETYENABLE=1), sets RC link-loss Return-to-Launch failsafe, and 15m climb altitude."}
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                  <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      checked={calibrateSensors}
                      onChange={(e) => setCalibrateSensors(e.target.checked)}
                      className="rounded text-emerald-500 focus:ring-emerald-500"
                    />
                    <span>Run automatic Level Horizon, Gyro, and Barometer ground zeroing</span>
                  </label>

                  <Button
                    size="md"
                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/20 shrink-0"
                    onPress={handleExecuteAutoSetup}
                  >
                    {isRunningSetup ? (
                      <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 mr-1.5" />
                    )}
                    <span>{isRunningSetup ? "Executing..." : "Run Auto-Setup"}</span>
                  </Button>
                </div>
              </Card>

              {/* Live Steps Execution Audit */}
              {setupSteps.length > 0 && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-bold text-foreground">
                    <span>Configuration Audit Log</span>
                    <span className="text-emerald-500">
                      {setupSteps.filter((s) => s.ok).length}/{setupSteps.length} Succeeded
                    </span>
                  </div>

                  <div className="max-h-48 overflow-y-auto flex flex-col gap-1.5 p-2 bg-surface-secondary rounded-2xl border border-border">
                    {setupSteps.map((step, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded-xl bg-surface border border-border/60 text-xs font-mono"
                      >
                        <div className="flex items-center gap-2">
                          {step.ok ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                          )}
                          <span className="font-semibold text-foreground">{step.step}</span>
                          <span className="text-muted text-[11px] hidden sm:inline">
                            — {step.description}
                          </span>
                        </div>
                        <span className={`text-[11px] ${step.ok ? "text-emerald-500" : "text-amber-500"}`}>
                          {step.detail}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Pre-Arm Readiness Inspection */}
          {activeTab === "prearm" && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-foreground">Pre-Flight Sanity Inspection</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs font-semibold px-2 text-muted hover:text-foreground"
                    onPress={loadPrearm}
                  >
                    {isLoadingPrearm ? (
                      <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5 mr-1" />
                    )}
                    <span>Re-check</span>
                  </Button>
                </div>

                {prearmReport && (
                  <Chip
                    size="sm"
                    variant="soft"
                    color={prearmReport.ready ? "success" : "warning"}
                    className="font-bold text-xs"
                  >
                    Readiness Score: {prearmReport.score}%
                  </Chip>
                )}
              </div>

              {prearmReport ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {prearmReport.checks.map((check, idx) => (
                    <Card
                      key={idx}
                      className="p-3 bg-surface-secondary border border-border rounded-2xl flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground">{check.name}</span>
                        <Chip
                          size="sm"
                          variant="soft"
                          color={
                            check.status === "PASS" || check.status === "READY"
                              ? "success"
                              : check.status === "WARN"
                              ? "warning"
                              : "danger"
                          }
                          className="text-[10px] font-mono h-5"
                        >
                          {check.status}
                        </Chip>
                      </div>
                      <span className="text-[11px] text-muted mt-2 font-mono">{check.detail}</span>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-muted">
                  Evaluating sensor and telemetry signals...
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Parameter Catalog & Live Editor */}
          {activeTab === "params" && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className="flex-1 flex items-center bg-surface-secondary rounded-xl px-3 py-1.5 border border-border">
                  <Search className="w-4 h-4 text-muted mr-2 shrink-0" />
                  <input
                    type="text"
                    value={paramSearch}
                    onChange={(e) => setParamSearch(e.target.value)}
                    placeholder="Filter parameters (e.g. ARMING_CHECK, MOT_SPIN_ARM)..."
                    className="w-full bg-transparent text-xs text-foreground placeholder:text-muted outline-none"
                  />
                </div>

                <Button
                  size="sm"
                  variant="ghost"
                  className="h-8 text-xs font-semibold px-2.5 text-muted hover:text-foreground"
                  onPress={loadParams}
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  <span>Refresh</span>
                </Button>
              </div>

              <div className="max-h-72 overflow-y-auto flex flex-col gap-2 p-1">
                {filteredParams.map((p) => {
                  const isEditing = editingParam?.name === p.name;
                  return (
                    <Card
                      key={p.name}
                      className="p-3 bg-surface-secondary border border-border rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                    >
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-foreground">{p.name}</span>
                          <Chip size="sm" variant="soft" className="text-[10px] h-4 font-mono">
                            {p.category}
                          </Chip>
                        </div>
                        <span className="text-[11px] text-muted mt-0.5">{p.description}</span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {isEditing ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              step="any"
                              value={editingParam.value}
                              onChange={(e) =>
                                setEditingParam({ name: p.name, value: parseFloat(e.target.value) || 0 })
                              }
                              className="w-20 px-2 py-1 text-xs font-mono bg-surface border border-border rounded-lg text-foreground outline-none"
                            />
                            <Button
                              size="sm"
                              className="bg-emerald-500 text-white font-bold text-xs h-7 px-2.5 rounded-lg"
                              onPress={() => handleWriteParam(p.name, editingParam.value)}
                            >
                              {isWritingParam ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                "Save"
                              )}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs h-7 px-2 rounded-lg"
                              onPress={() => setEditingParam(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                              {p.value}
                            </span>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs h-7 px-2.5 rounded-lg border border-border hover:bg-surface text-foreground"
                              onPress={() => setEditingParam({ name: p.name, value: p.value })}
                            >
                              Edit
                            </Button>
                          </div>
                        )}
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab 4: Sensors & Zeroing */}
          {activeTab === "calibration" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Card className="p-4 bg-surface-secondary border border-border rounded-2xl flex flex-col justify-between gap-3">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Level Horizon Calibration</span>
                  <span className="text-[11px] text-muted mt-1">
                    Place drone on flat table or desk. Zeroes vehicle roll and pitch offsets.
                  </span>
                </div>
                <Button
                  size="sm"
                  className="bg-surface border border-border hover:bg-surface-tertiary text-foreground font-semibold text-xs rounded-xl"
                  onPress={() => onCommand("calibrate_level")}
                >
                  Zero Horizon
                </Button>
              </Card>

              <Card className="p-4 bg-surface-secondary border border-border rounded-2xl flex flex-col justify-between gap-3">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Gyroscope Bias Nulling</span>
                  <span className="text-[11px] text-muted mt-1">
                    Hold drone completely still for 3 seconds while rate gyros sample baseline.
                  </span>
                </div>
                <Button
                  size="sm"
                  className="bg-surface border border-border hover:bg-surface-tertiary text-foreground font-semibold text-xs rounded-xl"
                  onPress={() => onCommand("calibrate_gyros")}
                >
                  Calibrate Gyros
                </Button>
              </Card>

              <Card className="p-4 bg-surface-secondary border border-border rounded-2xl flex flex-col justify-between gap-3">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Barometer Ground Zero</span>
                  <span className="text-[11px] text-muted mt-1">
                    Samples current ambient atmospheric pressure to set ground level to 0.0m AGL.
                  </span>
                </div>
                <Button
                  size="sm"
                  className="bg-surface border border-border hover:bg-surface-tertiary text-foreground font-semibold text-xs rounded-xl"
                  onPress={() => onCommand("calibrate_baro")}
                >
                  Zero Barometer
                </Button>
              </Card>

              <Card className="p-4 bg-surface-secondary border border-border rounded-2xl flex flex-col justify-between gap-3">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">Compass Magnetometer Calibration</span>
                  <span className="text-[11px] text-muted mt-1">
                    Triggers 3D spherical point sampling. Rotate drone slowly around all 3 axes.
                  </span>
                </div>
                <Button
                  size="sm"
                  className="bg-surface border border-border hover:bg-surface-tertiary text-foreground font-semibold text-xs rounded-xl"
                  onPress={() => onCommand("calibrate_compass")}
                >
                  Start Compass Calibration
                </Button>
              </Card>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border pt-4 mt-4">
          <span className="text-[11px] text-muted">
            Guardia AI v2.0.0 · ArduPilot & Pixhawk Direct Telemetry Bridge
          </span>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs font-semibold px-4 rounded-xl"
            onPress={onClose}
          >
            Close
          </Button>
        </div>
      </Card>
    </div>
  );
}
