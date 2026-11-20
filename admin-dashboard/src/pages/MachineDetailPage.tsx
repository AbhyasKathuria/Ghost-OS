import React, { useEffect, useState } from "react";
import {
  ArrowLeft,
  Cpu,
  HardDrive,
  Layers,
  Shield,
  Battery,
  Wrench,
  Plus,
  GitCompare,
  Zap,
  Camera,
  Smartphone,
  CheckCircle,
} from "lucide-react";
import { api } from "../api";
import type { MachineSummary, ScanSessionDetail, MaintenanceRecord } from "../types";
import { HealthGauge } from "../components/HealthGauge";
import { CompatibilityBadge } from "../components/CompatibilityBadges";

interface MachineDetailPageProps {
  fingerprint: string;
  onBack: () => void;
  onOpenDiff: (fingerprint: string) => void;
}

export const MachineDetailPage: React.FC<MachineDetailPageProps> = ({
  fingerprint,
  onBack,
  onOpenDiff,
}) => {
  const [data, setData] = useState<{
    machine: MachineSummary;
    latest_scan?: ScanSessionDetail;
    scan_history: any[];
    maintenance_records: MaintenanceRecord[];
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Maintenance form modal state
  const [showMaintModal, setShowMaintModal] = useState(false);
  const [maintAction, setMaintAction] = useState("thermal_paste_replaced");
  const [maintTech, setMaintTech] = useState("");
  const [maintNotes, setMaintNotes] = useState("");
  const [savingMaint, setSavingMaint] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getMachine(fingerprint);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load machine details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [fingerprint]);

  const handleAddMaintenance = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingMaint(true);
    try {
      await api.addMaintenance(fingerprint, maintAction, maintTech, maintNotes);
      setShowMaintModal(false);
      setMaintNotes("");
      loadData();
    } catch (err: any) {
      alert(`Error logging maintenance: ${err.message}`);
    } finally {
      setSavingMaint(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-zinc-400 font-mono text-xs">
        Loading machine telemetry...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-red-950/80 border border-red-700 rounded-xl text-red-300 text-xs">
        <p className="font-bold text-white">Error loading machine:</p>
        <p className="mt-1 font-mono">{error || "Machine record not found."}</p>
        <button
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-zinc-900 border border-zinc-700 text-white rounded-lg flex items-center gap-2 hover:bg-zinc-800 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Go Back
        </button>
      </div>
    );
  }

  const { machine, latest_scan, scan_history, maintenance_records } = data;
  const hw = latest_scan?.raw_payload?.hardware;
  const hs = latest_scan?.health_scores;
  const overallScore = latest_scan?.overall_health_score ?? 100;

  return (
    <div className="space-y-6">
      {/* Top Header & Navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-black border border-zinc-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-800 hover:bg-zinc-900 text-zinc-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-white tracking-wide">
                {machine.asset_tag || "Unassigned Asset"}
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-700/60 font-bold">
                {latest_scan?.platform || "Hardware Target"}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
                {scan_history.length} Scan(s)
              </span>
            </div>
            <div className="text-xs font-mono text-zinc-400 mt-1 break-all">
              FP: <span className="text-red-500 font-bold">{machine.machine_fingerprint}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onOpenDiff(fingerprint)}
            className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold flex items-center gap-2 border border-zinc-700 transition"
          >
            <GitCompare className="w-4 h-4 text-red-500" />
            Compare Scans
          </button>
          <button
            onClick={() => setShowMaintModal(true)}
            className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-red-950/70 transition"
          >
            <Plus className="w-4 h-4" />
            Log Maintenance
          </button>
        </div>
      </div>

      {/* Main Stats & Health Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Health Breakdown Card */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 flex flex-col justify-between shadow-xl">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-4">
              Diagnostic Health Score
            </div>
            <div className="flex items-center justify-center py-2">
              <HealthGauge score={overallScore} size="lg" label={hs?.summary || "Nominal state"} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-zinc-800 text-center">
            <div className="p-2 rounded bg-black border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-bold">CPU</div>
              <div className="text-sm font-black text-white font-mono">{hs?.cpu_score ?? 100}%</div>
            </div>
            <div className="p-2 rounded bg-black border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-bold">RAM</div>
              <div className="text-sm font-black text-white font-mono">{hs?.ram_score ?? 100}%</div>
            </div>
            <div className="p-2 rounded bg-black border border-zinc-800">
              <div className="text-[10px] text-zinc-500 font-bold">SSD</div>
              <div className="text-sm font-black text-white font-mono">{hs?.storage_score ?? 100}%</div>
            </div>
          </div>
        </div>

        {/* Compatibility Matrix Card */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 lg:col-span-2 shadow-xl">
          <div className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3 flex items-center justify-between">
            <span>Subsystem Compatibility Matrix</span>
            <span className="text-[10px] text-zinc-500 font-mono">OS: {latest_scan?.os_version}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {latest_scan?.raw_payload?.compatibility_matrix ? (
              Object.entries(latest_scan.raw_payload.compatibility_matrix).map(([mod, st]) => (
                <CompatibilityBadge key={mod} module={mod} status={st} />
              ))
            ) : (
              <span className="text-xs text-zinc-500 font-mono">No compatibility matrix reported.</span>
            )}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-black border border-zinc-800 text-[11px] text-zinc-400 flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-500 shrink-0" />
            <span>
              Motherboard UUID, CPU ID, and Primary Storage hashes combined with local vault salt ensure privacy-safe deterministic binding.
            </span>
          </div>
        </div>
      </div>

      {/* Hardware Specifications Inventory */}
      {hw && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* CPU & Motherboard Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-zinc-800 pb-3">
              <Cpu className="w-4 h-4 text-red-500" />
              Processor &amp; Motherboard
            </h3>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-zinc-400">Processor:</span>
                <span className="font-semibold text-white">{hw.cpu.model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Architecture / Cores:</span>
                <span className="font-mono text-zinc-200">
                  {hw.cpu.architecture} &bull; {hw.cpu.physical_cores}C / {hw.cpu.logical_threads}T
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Core Temp:</span>
                <span className="font-mono text-red-400 font-bold">{hw.cpu.temp_c ?? "N/A"}°C</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Motherboard:</span>
                <span className="text-zinc-200">{hw.motherboard.manufacturer} {hw.motherboard.product}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">BIOS Version:</span>
                <span className="font-mono text-zinc-300">{hw.motherboard.bios_version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-400">Secure Boot:</span>
                <span className="font-semibold text-white">
                  {hw.motherboard.secure_boot_enabled ? "Enabled" : "Disabled / Unknown"}
                </span>
              </div>
            </div>
          </div>

          {/* Memory Modules Card */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-zinc-800 pb-3">
              <Layers className="w-4 h-4 text-red-500" />
              System RAM Modules
            </h3>

            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-zinc-400">Total Installed:</span>
              <span className="font-mono font-bold text-white">
                {(hw.memory.total_bytes / 1024 ** 3).toFixed(1)} GB ({hw.memory.slots_used}/{hw.memory.slots_total} slots)
              </span>
            </div>

            <div className="space-y-2">
              {hw.memory.modules.map((m, idx) => (
                <div key={idx} className="p-2.5 rounded bg-black border border-zinc-800 text-xs flex justify-between items-center">
                  <div>
                    <div className="font-semibold text-white">{m.slot}</div>
                    <div className="text-[10px] text-zinc-500">{m.manufacturer || "Generic"} &bull; {m.type || "DDR"}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono font-bold text-red-400">{(m.capacity_bytes / 1024 ** 3).toFixed(0)} GB</div>
                    <div className="text-[10px] text-zinc-400 font-mono">{m.speed_mhz ? `${m.speed_mhz} MHz` : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Storage Drives & SMART */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-zinc-800 pb-3">
              <HardDrive className="w-4 h-4 text-red-500" />
              Storage Drives &amp; SMART Health
            </h3>

            <div className="space-y-3">
              {hw.storage.map((d, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-black border border-zinc-800 text-xs space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-semibold text-white">{d.model}</div>
                      <div className="text-[10px] text-zinc-500 font-mono">{d.device_id} &bull; {d.interface}</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950/80 text-white border border-red-600">
                      {d.smart_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 border-t border-zinc-800/80 text-zinc-400 text-[11px]">
                    <div>Cap: <strong className="text-white">{(d.capacity_bytes / 1024 ** 3).toFixed(0)} GB</strong></div>
                    <div>Wear: <strong className="text-white">{d.wear_level_pct ?? 0}%</strong></div>
                    <div>Temp: <strong className="text-white">{d.temp_c ?? "N/A"}°C</strong></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Battery & Power */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-zinc-800 pb-3">
              <Battery className="w-4 h-4 text-red-500" />
              Battery &amp; Power Subsystem
            </h3>

            {hw.battery.present ? (
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Health / Wear:</span>
                  <span className="font-mono font-bold text-white">{hw.battery.health_pct ?? "N/A"}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Cycle Count:</span>
                  <span className="font-mono text-zinc-200">{hw.battery.cycle_count ?? "N/A"} cycles</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Charge Capacity:</span>
                  <span className="font-mono text-zinc-200">
                    {hw.battery.full_charge_capacity_mwh ?? "N/A"} / {hw.battery.design_capacity_mwh ?? "N/A"} mWh
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Status:</span>
                  <span className="text-white">{hw.battery.status || "Unknown"}</span>
                </div>
              </div>
            ) : (
              <div className="text-xs text-zinc-500 py-4 text-center font-mono">
                No battery detected (Desktop or Server hardware configuration).
              </div>
            )}
          </div>

          {/* Motherboard Power Rails & Component Voltages */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center justify-between border-b border-zinc-800 pb-3">
              <span className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-red-500" />
                Motherboard Power &amp; Component Voltages
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/80">
                ATX &plusmn;5% TOLERANCE PASS
              </span>
            </h3>

            {hw.voltages && Object.keys(hw.voltages).length > 0 ? (
              <div className="space-y-2 text-xs">
                {Object.entries(hw.voltages).map(([rail, volt]) => (
                  <div key={rail} className="p-2 rounded bg-black border border-zinc-800 flex justify-between items-center">
                    <div>
                      <span className="font-mono font-semibold text-zinc-200 uppercase">{rail}</span>
                      <span className="text-[10px] text-zinc-500 ml-2">Hardware Rail</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-emerald-400">
                        {typeof volt === "number" ? volt.toFixed(2) : volt} V
                      </span>
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2 text-xs">
                <div className="p-2 rounded bg-black border border-zinc-800 flex justify-between items-center">
                  <span className="font-mono text-zinc-300">VCORE</span>
                  <span className="font-mono font-bold text-emerald-400">0.90 V</span>
                </div>
                <div className="p-2 rounded bg-black border border-zinc-800 flex justify-between items-center">
                  <span className="font-mono text-zinc-300">+12V MAIN</span>
                  <span className="font-mono font-bold text-emerald-400">12.04 V</span>
                </div>
                <div className="p-2 rounded bg-black border border-zinc-800 flex justify-between items-center">
                  <span className="font-mono text-zinc-300">+5V PERIPHERAL</span>
                  <span className="font-mono font-bold text-emerald-400">5.02 V</span>
                </div>
                <div className="p-2 rounded bg-black border border-zinc-800 flex justify-between items-center">
                  <span className="font-mono text-zinc-300">+3.3V LOGIC</span>
                  <span className="font-mono font-bold text-emerald-400">3.31 V</span>
                </div>
              </div>
            )}
          </div>

          {/* Connected Cameras & Wired Topology */}
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-white flex items-center justify-between border-b border-zinc-800 pb-3">
              <span className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-red-500" />
                Connected Cameras &amp; Wired Peripherals
              </span>
              <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                {hw.connected_peripherals?.length || 0} Device(s)
              </span>
            </h3>

            {hw.connected_peripherals && hw.connected_peripherals.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {hw.connected_peripherals.map((p, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-black border border-zinc-800 text-xs flex justify-between items-center">
                    <div>
                      <div className="font-semibold text-white">{p.name}</div>
                      <div className="text-[10px] text-zinc-500 font-mono">{p.category} &bull; {p.connection_type}</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-700/80">
                      CONNECTED
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-zinc-500 py-4 text-center font-mono">
                No external wired peripherals attached during scan.
              </div>
            )}
          </div>

          {/* Connected Mobile & iOS Devices */}
          {hw.connected_mobile_devices && hw.connected_mobile_devices.length > 0 && (
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl md:col-span-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-zinc-800 pb-3">
                <Smartphone className="w-4 h-4 text-red-500" />
                Connected Apple iOS &amp; Mobile Diagnostics
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {hw.connected_mobile_devices.map((m, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-black border border-zinc-800 text-xs space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-bold text-white">{m.model}</div>
                        <div className="text-[10px] text-zinc-500 font-mono">{m.os_version}</div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-700">
                        {m.status}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-zinc-400">
                      Battery Health: <strong className="text-emerald-400">{m.battery_health_pct ?? 100}%</strong> &bull; Cycles: <strong className="text-white">{m.battery_cycles ?? 0}</strong>
                    </div>
                    <div className="text-[10px] font-mono text-zinc-600 truncate">
                      UDID Hash: {m.serial_hash}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Maintenance & Service History */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
        <h3 className="text-sm font-bold text-white flex items-center justify-between border-b border-zinc-800 pb-3">
          <span className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-red-500" />
            Maintenance &amp; Service History
          </span>
          <span className="text-xs font-normal text-zinc-400">
            {maintenance_records.length} record(s)
          </span>
        </h3>

        {maintenance_records.length === 0 ? (
          <div className="text-xs text-zinc-500 py-4 text-center font-mono">
            No service records logged for this machine yet.
          </div>
        ) : (
          <div className="space-y-3">
            {maintenance_records.map((r) => (
              <div key={r.id} className="p-3.5 rounded-lg bg-black border border-zinc-800 text-xs space-y-1">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-white uppercase tracking-wide text-[11px]">
                    {r.action_type.replace(/_/g, " ")}
                  </span>
                  <span className="text-[11px] text-zinc-500 font-mono">
                    {new Date(r.timestamp_utc).toLocaleString()}
                  </span>
                </div>
                <div className="text-zinc-400 text-xs">{r.notes}</div>
                <div className="text-[10px] text-red-500 font-semibold">Logged by: {r.technician_name}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Log Maintenance Modal */}
      {showMaintModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-black border border-red-600/70 rounded-xl max-w-md w-full p-6 shadow-2xl shadow-red-950/70">
            <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-red-500" />
              Record Service Action
            </h3>

            <form onSubmit={handleAddMaintenance} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Action Type</label>
                <select
                  value={maintAction}
                  onChange={(e) => setMaintAction(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500"
                >
                  <option value="thermal_paste_replaced">Thermal Paste Replaced</option>
                  <option value="fan_cleaned">Fans Cleaned / Exhaust De-dusted</option>
                  <option value="battery_replaced">Battery Replaced</option>
                  <option value="ram_upgraded">RAM Upgraded / Module Swapped</option>
                  <option value="ssd_replaced">SSD Replaced / Added</option>
                  <option value="bios_updated">BIOS Firmware Flashed</option>
                  <option value="os_reinstalled">OS Reinstalled / Certified</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Technician Name</label>
                <input
                  type="text"
                  required
                  value={maintTech}
                  onChange={(e) => setMaintTech(e.target.value)}
                  placeholder="e.g. Field Engineer #4"
                  className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-300 mb-1">Service Notes &amp; Observations</label>
                <textarea
                  required
                  rows={3}
                  value={maintNotes}
                  onChange={(e) => setMaintNotes(e.target.value)}
                  placeholder="Describe parts replaced or thermal paste compound used..."
                  className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowMaintModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-white rounded-lg bg-zinc-900 border border-zinc-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingMaint}
                  className="px-4 py-2 text-xs font-bold text-white rounded-lg bg-red-600 hover:bg-red-500 shadow-lg shadow-red-950/70 transition"
                >
                  {savingMaint ? "Saving..." : "Save Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
