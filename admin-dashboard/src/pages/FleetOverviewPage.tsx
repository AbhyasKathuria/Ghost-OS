import React, { useEffect, useState } from "react";
import {
  HardDrive,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  Search,
  ExternalLink,
  RefreshCw,
  Usb,
  Clock,
} from "lucide-react";
import { api } from "../api";
import type { MachineSummary } from "../types";

interface FleetOverviewPageProps {
  onSelectMachine: (fingerprint: string) => void;
  onOpenDiff: (fingerprint: string) => void;
}

export const FleetOverviewPage: React.FC<FleetOverviewPageProps> = ({
  onSelectMachine,
  onOpenDiff,
}) => {
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchMachines = async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await api.listMachines(search);
      setMachines(data);
    } catch (err: any) {
      if (!silent) setError(err.message || "Failed to load machines.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
    const interval = setInterval(() => {
      fetchMachines(true);
    }, 4000);
    return () => clearInterval(interval);
  }, [search]);

  // Aggregate Metrics
  const totalMachines = machines.length;
  const totalScans = machines.reduce((acc, m) => acc + (m.scan_count || 0), 0);
  const criticalCount = machines.filter(
    (m) => m.latest_health_score !== undefined && m.latest_health_score < 70,
  ).length;

  return (
    <div className="space-y-6">
      {/* Top Welcome & USB Banner */}
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div>
          <h1 className="text-xl font-black text-white tracking-wide flex items-center gap-2">
            <span>Fleet Intelligence Overview</span>
            <span className="text-xs px-2 py-0.5 rounded bg-red-950 border border-red-700 text-red-400 font-mono font-bold">
              OFFLINE
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Authoritative hardware audit and degradation tracking stored exclusively in Ghost Vault.
          </p>
        </div>

        {/* USB Storage Health Indicator */}
        <div className="flex items-center gap-3 bg-zinc-950 border border-zinc-800 px-4 py-2.5 rounded-xl">
          <div className="p-2 rounded-lg bg-red-950/80 text-red-500 border border-red-700/60 shadow-inner">
            <Usb className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-zinc-400">USB Vault Storage (exFAT)</div>
            <div className="text-xs font-mono text-white font-bold">100% HEALTH &bull; WAL-SAFE</div>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Total Machines</div>
            <div className="text-2xl font-black font-mono text-white mt-1">{totalMachines}</div>
            <div className="text-[11px] text-zinc-500 mt-1 font-mono">Unique Hardware Fingerprints</div>
          </div>
          <div className="p-3 rounded-xl bg-red-950/60 border border-red-700/50 text-red-500">
            <Cpu className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Scan Telemetry</div>
            <div className="text-2xl font-black font-mono text-white mt-1">{totalScans}</div>
            <div className="text-[11px] text-zinc-500 mt-1 font-mono">Windows &amp; Linux sessions</div>
          </div>
          <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-700 text-white">
            <HardDrive className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Health Nominal</div>
            <div className="text-2xl font-black font-mono text-white mt-1">
              {totalMachines - criticalCount}
            </div>
            <div className="text-[11px] text-zinc-500 mt-1 font-mono">Score &gt;= 70/100</div>
          </div>
          <div className="p-3 rounded-xl bg-red-950/60 border border-red-700/50 text-red-500">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Attention Needed</div>
            <div className="text-2xl font-black font-mono text-red-500 mt-1">{criticalCount}</div>
            <div className="text-[11px] text-zinc-500 mt-1 font-mono">Critical SMART / Thermals</div>
          </div>
          <div className="p-3 rounded-xl bg-red-950 border border-red-600 text-red-500">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Machine Fleet Registry Table */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-5 border-b border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>Machine Registry</span>
            <span className="text-xs text-zinc-400 font-normal">({machines.length} registered)</span>
          </h2>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search asset, fingerprint..."
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-black border border-zinc-800 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-red-500 font-mono"
              />
            </div>
            <button
              onClick={() => fetchMachines(false)}
              className="p-2 rounded-lg bg-black border border-zinc-800 hover:bg-zinc-900 text-zinc-400 hover:text-white transition cursor-pointer"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-950/80 border-b border-red-700 text-red-300 text-xs font-mono">
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
              <tr>
                <th className="py-3.5 px-4 font-bold">Machine Fingerprint</th>
                <th className="py-3.5 px-4 font-bold">Asset Tag</th>
                <th className="py-3.5 px-4 font-bold text-center">Health</th>
                <th className="py-3.5 px-4 font-bold text-center">Scans</th>
                <th className="py-3.5 px-4 font-bold">Last Audited</th>
                <th className="py-3.5 px-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/70">
              {machines.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-zinc-500 font-mono">
                    {loading ? "Loading machine registry..." : "No machines scanned yet. Plug USB and run scan to record hardware."}
                  </td>
                </tr>
              ) : (
                machines.map((m) => {
                  const score = m.latest_health_score ?? 100;
                  return (
                    <tr
                      key={m.machine_fingerprint}
                      className="hover:bg-zinc-900/60 transition group cursor-pointer"
                      onClick={() => onSelectMachine(m.machine_fingerprint)}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-mono text-red-500 font-bold group-hover:text-red-400">
                          {m.machine_fingerprint.slice(0, 16)}...
                        </div>
                        <div className="text-[10px] text-zinc-500 font-mono">
                          SHA-256 Anchor
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-semibold text-white">
                          {m.asset_tag || <span className="text-zinc-600 italic">Unassigned</span>}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`font-mono font-bold px-2 py-0.5 rounded text-xs ${
                            score >= 85
                              ? "bg-red-950/60 text-white border border-red-600/70"
                              : score >= 70
                              ? "bg-zinc-900 text-zinc-300 border border-zinc-700"
                              : "bg-red-950 text-red-400 border border-red-700"
                          }`}
                        >
                          {score}/100
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono font-bold text-white">
                        {m.scan_count}
                      </td>
                      <td className="py-3.5 px-4 text-zinc-400 font-mono">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-zinc-500" />
                          <span>{m.latest_scan_utc ? new Date(m.latest_scan_utc).toLocaleDateString() : "Never"}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => onOpenDiff(m.machine_fingerprint)}
                            title="Compare Scans & Changes"
                            className="p-1.5 rounded-lg bg-zinc-900 hover:bg-red-950 text-zinc-400 hover:text-white border border-zinc-800 transition"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
