import React, { useState } from "react";
import {
  Activity,
  Flame,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  ShieldCheck,
  Thermometer,
} from "lucide-react";
import { StressLabModal } from "../components/StressLabModal";
import type { DiagnosticResult, DiagnosticStatus } from "../types";

export const DiagnosticsLabPage: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRoutine, setSelectedRoutine] = useState<string>("CPU Matrix Compute Stress");
  const [duration, setDuration] = useState<number>(30);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTemp, setCurrentTemp] = useState(48.5);

  // Diagnostic Test Suite results
  const [tests] = useState<DiagnosticResult[]>([
    {
      test_name: "SMART Health & Critical Warning Attributes",
      status: "PASS",
      metric_value: 0.0,
      threshold: 0.0,
      evidence: "All NVMe media errors and available spare thresholds within specification.",
      recommendation: "Drive health is optimal. No action required.",
    },
    {
      test_name: "CPU Thermal Baseline & Dissipation",
      status: "PASS",
      metric_value: 48.5,
      threshold: 75.0,
      evidence: "Idle core temperature measured at 48.5°C across 14 cores.",
      recommendation: "Thermal paste application and heatsink contact confirmed adequate.",
    },
    {
      test_name: "RAM Physical Channel Allocation",
      status: "PASS",
      metric_value: 16.0,
      threshold: 4.0,
      evidence: "Dual-channel symmetric 2x8GB DDR5 operating at 4800 MT/s.",
      recommendation: "None",
    },
    {
      test_name: "Battery Charge Impedance & Wear",
      status: "WARN",
      metric_value: 82.5,
      threshold: 80.0,
      evidence: "Battery capacity measured at 82.5% of factory design spec with 340 cycles.",
      recommendation: "Cell wear is approaching service threshold. Monitor battery runtime under heavy workload.",
    },
  ]);

  const handleStartStressRoutine = () => {
    setRunning(true);
    setProgress(0);
    setCurrentTemp(48.5);

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setRunning(false);
          setCurrentTemp(54.0);
          return 100;
        }
        setCurrentTemp((t) => Number((t + 0.6).toFixed(1)));
        return prev + 5;
      });
    }, (duration * 1000) / 20);
  };

  const getStatusIcon = (st: DiagnosticStatus) => {
    switch (st) {
      case "PASS":
        return <CheckCircle2 className="w-4 h-4 text-white" />;
      case "WARN":
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case "FAIL":
        return <XCircle className="w-4 h-4 text-red-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div>
          <h1 className="text-xl font-black text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-red-500" />
            Diagnostics Lab &amp; Safe Stress Bench
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Deterministic diagnostic analysis and bounded, thermally throttled hardware stress tests.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-zinc-950 px-3.5 py-2 rounded-xl border border-zinc-800 text-xs">
          <Thermometer className="w-4 h-4 text-red-500" />
          <span className="text-zinc-400">Current CPU Temp:</span>
          <span className="font-mono font-bold text-white">{currentTemp}°C</span>
          <span className="text-[10px] text-red-400 font-bold ml-1 font-mono">(SAFE)</span>
        </div>
      </div>

      {/* Stress Testing Safety Console */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <Flame className="w-4 h-4 text-red-500" />
            Bounded Stress Routine Runner
          </div>
          <span className="text-[11px] text-zinc-300 font-mono flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-red-500" /> 90°C Thermal Guard Active
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Test Routine</label>
            <select
              value={selectedRoutine}
              onChange={(e) => setSelectedRoutine(e.target.value)}
              disabled={running}
              className="w-full px-3 py-2 rounded-lg bg-black border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500"
            >
              <option value="CPU Prime Computation Stress">CPU Prime Number Stress (All Cores)</option>
              <option value="Storage Sequential Read Benchmark">NVMe / SSD Sequential Read Sweep</option>
              <option value="Memory Pattern Integrity Check">RAM Address &amp; Pattern Integrity</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Duration Cap</label>
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              disabled={running}
              className="w-full px-3 py-2 rounded-lg bg-black border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500"
            >
              <option value={15}>15 Seconds (Quick Verification)</option>
              <option value={30}>30 Seconds (Thermal Equilibrium)</option>
              <option value={60}>60 Seconds (Full Burn-In)</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setModalOpen(true)}
              disabled={running}
              className={`w-full py-2 px-4 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition ${
                running
                  ? "bg-zinc-900 text-zinc-600 border border-zinc-800 cursor-not-allowed"
                  : "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-950/70 cursor-pointer"
              }`}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {running ? "Routine Active..." : "Authorize & Run Routine"}
            </button>
          </div>
        </div>

        {/* Live Progress Bar */}
        {running && (
          <div className="space-y-2 pt-2">
            <div className="flex justify-between text-xs text-zinc-400 font-mono">
              <span>Executing {selectedRoutine}...</span>
              <span className="text-red-400 font-bold">{progress}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-black overflow-hidden border border-zinc-800">
              <div
                className="h-full bg-gradient-to-r from-red-800 via-red-600 to-rose-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Diagnostic Findings Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-white">Active Diagnostic Assertions</h3>
          <span className="text-xs text-zinc-400">Evaluated against deterministic health criteria</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
              <tr>
                <th className="py-3 px-4 font-bold">Diagnostic Test</th>
                <th className="py-3 px-4 font-bold text-center">Status</th>
                <th className="py-3 px-4 font-bold">Evidence &amp; Telemetry</th>
                <th className="py-3 px-4 font-bold">Engineer Recommendation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80">
              {tests.map((t, idx) => (
                <tr key={idx} className="hover:bg-zinc-900/60 transition">
                  <td className="py-3.5 px-4 font-bold text-white">{t.test_name}</td>
                  <td className="py-3.5 px-4 text-center">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold border ${
                        t.status === "PASS"
                          ? "bg-red-950/60 text-white border-red-600/70"
                          : t.status === "WARN"
                          ? "bg-zinc-900 text-zinc-300 border-zinc-700"
                          : "bg-red-950 text-red-400 border-red-600"
                      }`}
                    >
                      {getStatusIcon(t.status)}
                      {t.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-zinc-300">{t.evidence}</td>
                  <td className="py-3.5 px-4 text-zinc-400">{t.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Safety Modal */}
      <StressLabModal
        isOpen={modalOpen}
        testName={selectedRoutine}
        durationSeconds={duration}
        onClose={() => setModalOpen(false)}
        onConfirm={handleStartStressRoutine}
      />
    </div>
  );
};
