import React, { useEffect, useState } from "react";
import {
  GitCompare,
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { api } from "../api";
import type { HardwareDiffReport, MachineSummary } from "../types";

interface DiffViewerPageProps {
  initialFingerprint?: string;
}

export const DiffViewerPage: React.FC<DiffViewerPageProps> = ({ initialFingerprint }) => {
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [selectedFingerprint, setSelectedFingerprint] = useState(initialFingerprint || "");
  const [diffReport, setDiffReport] = useState<HardwareDiffReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available machines
  useEffect(() => {
    api.listMachines().then((list) => {
      setMachines(list);
      if (!selectedFingerprint && list.length > 0) {
        setSelectedFingerprint(list[0].machine_fingerprint);
      }
    });
  }, []);

  // Compute diff when machine changes
  const runDiff = async (fp: string) => {
    if (!fp) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getMachineDiff(fp);
      setDiffReport(res);
    } catch (err: any) {
      setError(err.message || "Failed to compute hardware diff. Machine may only have a single scan.");
      setDiffReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFingerprint) {
      runDiff(selectedFingerprint);
    }
  }, [selectedFingerprint]);

  const getChangeBadge = (type: string) => {
    switch (type) {
      case "UPGRADE":
        return "bg-zinc-900 text-white border-zinc-700";
      case "REPLACEMENT":
        return "bg-red-950/70 text-red-300 border-red-700/60";
      case "DEGRADATION":
        return "bg-red-950 text-red-400 border-red-600 font-bold";
      case "FIRMWARE_CONFIG":
        return "bg-zinc-900 text-zinc-300 border-zinc-800";
      case "REMOVAL":
        return "bg-red-950/50 text-red-400 border-red-800";
      default:
        return "bg-black text-zinc-400 border-zinc-800";
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Machine Selector */}
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div>
          <h1 className="text-xl font-black text-white flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-red-500" />
            Hardware Change &amp; Degradation Diff Engine
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Automated timeline delta detection: component upgrades, replacements, and wear tracking.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedFingerprint}
            onChange={(e) => setSelectedFingerprint(e.target.value)}
            className="px-3.5 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500 font-mono"
          >
            {machines.map((m) => (
              <option key={m.machine_fingerprint} value={m.machine_fingerprint}>
                {m.asset_tag ? `${m.asset_tag} (${m.machine_fingerprint.slice(0, 10)}...)` : m.machine_fingerprint.slice(0, 18)}
              </option>
            ))}
          </select>
          <button
            onClick={() => runDiff(selectedFingerprint)}
            className="p-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800 transition cursor-pointer"
            title="Re-run Diff"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {loading && (
        <div className="text-center py-12 text-zinc-400 font-mono text-xs">
          Computing hardware deltas across historical scan sessions...
        </div>
      )}

      {error && (
        <div className="bg-red-950/80 border border-red-700 rounded-xl p-5 text-red-300 text-xs flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {diffReport && !loading && (
        <div className="space-y-6">
          {/* Comparison Baseline Banner */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-xs">
            <div>
              <span className="text-zinc-500">Baseline Session:</span>{" "}
              <strong className="text-white font-mono">{diffReport.baseline_scan_id.slice(0, 8)}</strong>{" "}
              <span className="text-zinc-500">({new Date(diffReport.baseline_timestamp_utc).toLocaleDateString()} &bull; {diffReport.baseline_platform})</span>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-600 hidden sm:block" />
            <div>
              <span className="text-zinc-500">Target Session:</span>{" "}
              <strong className="text-red-400 font-mono font-bold">{diffReport.current_scan_id.slice(0, 8)}</strong>{" "}
              <span className="text-zinc-500">({new Date(diffReport.current_timestamp_utc).toLocaleDateString()} &bull; {diffReport.current_platform})</span>
            </div>
          </div>

          {/* Degradation Alerts Section */}
          {diffReport.degradations.length > 0 && (
            <div className="bg-black border border-red-600 rounded-xl p-5 space-y-3 shadow-xl shadow-red-950/60">
              <h3 className="text-sm font-bold text-red-400 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-500" />
                Active Degradation &amp; Wear Warnings ({diffReport.degradations.length})
              </h3>
              <div className="space-y-2">
                {diffReport.degradations.map((deg, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-red-950/80 border border-red-700 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div>
                      <span className="font-bold text-white uppercase tracking-wider text-[11px] mr-2">
                        [{deg.component}]
                      </span>
                      <span className="text-zinc-200">{deg.description}</span>
                    </div>
                    <div className="font-mono text-red-400 font-bold shrink-0 text-[11px]">
                      {deg.old_value} &rarr; {deg.new_value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All Detected Changes Table */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">
                Detailed Component Delta Log ({diffReport.total_changes} items)
              </h3>
              <span className="text-xs text-zinc-400 font-mono">{diffReport.summary}</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-black text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
                  <tr>
                    <th className="py-3 px-4 font-bold">Subsystem</th>
                    <th className="py-3 px-4 font-bold">Classification</th>
                    <th className="py-3 px-4 font-bold">Delta Description</th>
                    <th className="py-3 px-4 font-bold font-mono">Historical Baseline</th>
                    <th className="py-3 px-4 font-bold font-mono text-red-400">Current Reading</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/80">
                  {diffReport.changes.length === 0 && diffReport.degradations.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-zinc-500 font-mono">
                        Zero component alterations or degradation detected between these scans.
                      </td>
                    </tr>
                  ) : (
                    [...diffReport.changes, ...diffReport.degradations].map((item, idx) => (
                      <tr key={idx} className="hover:bg-zinc-900/60 transition">
                        <td className="py-3 px-4 font-bold text-white">{item.component}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getChangeBadge(item.change_type)}`}>
                            {item.change_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-zinc-300">{item.description}</td>
                        <td className="py-3 px-4 font-mono text-zinc-400">{String(item.old_value)}</td>
                        <td className="py-3 px-4 font-mono text-white font-bold">{String(item.new_value)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
