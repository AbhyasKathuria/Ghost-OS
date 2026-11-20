import React, { useState } from "react";
import { Flame, X } from "lucide-react";

interface StressLabModalProps {
  isOpen: boolean;
  testName: string;
  durationSeconds: number;
  onClose: () => void;
  onConfirm: () => void;
}

export const StressLabModal: React.FC<StressLabModalProps> = ({
  isOpen,
  testName,
  durationSeconds,
  onClose,
  onConfirm,
}) => {
  const [acknowledgedThermal, setAcknowledgedThermal] = useState(false);
  const [acknowledgedBattery, setAcknowledgedBattery] = useState(false);

  if (!isOpen) return null;

  const canProceed = acknowledgedThermal && acknowledgedBattery;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      <div className="bg-black border border-red-600/70 rounded-xl max-w-lg w-full p-6 shadow-2xl shadow-red-950/60 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-900 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 text-red-500 mb-4">
          <div className="p-2.5 rounded-lg bg-red-950/80 border border-red-700/70 text-red-400 shadow-inner shadow-red-950">
            <Flame className="w-6 h-6 text-red-500 animate-pulse" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white tracking-wide">Active Stress Test Authorization</h3>
            <p className="text-xs text-red-500 font-mono tracking-wider font-bold">CAUTION: MAXIMUM HARDWARE LOAD</p>
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3.5 mb-5 text-xs text-zinc-300 space-y-2">
          <div className="flex justify-between">
            <span className="text-zinc-400">Target Routine:</span>
            <span className="font-semibold text-white">{testName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Duration Bound:</span>
            <span className="font-semibold text-red-400">{durationSeconds} seconds</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-400">Thermal Guardrail:</span>
            <span className="font-semibold text-white">Auto-cutoff at 90.0°C</span>
          </div>
        </div>

        <div className="space-y-3 mb-6">
          <label className="flex items-start gap-3 p-3 rounded-lg bg-zinc-950 border border-zinc-800 cursor-pointer hover:border-red-600/50 transition">
            <input
              type="checkbox"
              checked={acknowledgedThermal}
              onChange={(e) => setAcknowledgedThermal(e.target.checked)}
              className="mt-0.5 rounded border-zinc-700 bg-black text-red-600 focus:ring-red-500"
            />
            <span className="text-xs text-zinc-200">
              I acknowledge this routine induces 100% compute load. I verify host ventilation is unobstructed.
            </span>
          </label>

          <label className="flex items-start gap-3 p-3 rounded-lg bg-zinc-950 border border-zinc-800 cursor-pointer hover:border-red-600/50 transition">
            <input
              type="checkbox"
              checked={acknowledgedBattery}
              onChange={(e) => setAcknowledgedBattery(e.target.checked)}
              className="mt-0.5 rounded border-zinc-700 bg-black text-red-600 focus:ring-red-500"
            />
            <span className="text-xs text-zinc-200">
              I confirm the machine is connected to AC mains power or maintains &gt; 50% battery reserve.
            </span>
          </label>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-zinc-300 hover:text-white rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 transition"
          >
            Cancel
          </button>
          <button
            disabled={!canProceed}
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-5 py-2 text-xs font-bold rounded-lg transition flex items-center gap-2 ${
              canProceed
                ? "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-950/60 cursor-pointer"
                : "bg-zinc-900 text-zinc-600 border border-zinc-800 cursor-not-allowed"
            }`}
          >
            Start Stress Test
          </button>
        </div>
      </div>
    </div>
  );
};
