import React, { useEffect, useState } from "react";
import {
  FileText,
  Download,
  FileCode,
  FileSpreadsheet,
  FileType,
  Printer,
  ExternalLink,
} from "lucide-react";
import { api } from "../api";
import type { MachineSummary } from "../types";

export const ReportCenterPage: React.FC = () => {
  const [machines, setMachines] = useState<MachineSummary[]>([]);
  const [selectedMachine, setSelectedMachine] = useState<string>("");
  const [scans, setScans] = useState<any[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>("");

  useEffect(() => {
    api.listMachines().then((list) => {
      setMachines(list);
      if (list.length > 0) {
        setSelectedMachine(list[0].machine_fingerprint);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedMachine) {
      api.getMachine(selectedMachine).then((res) => {
        setScans(res.scan_history || []);
        if (res.scan_history && res.scan_history.length > 0) {
          setSelectedScanId(res.scan_history[0].scan_id);
        } else {
          setSelectedScanId("");
        }
      });
    }
  }, [selectedMachine]);

  const handleDownload = (format: "pdf" | "html" | "json" | "csv") => {
    if (!selectedScanId) return;
    const url = api.getExportUrl(selectedScanId, format);
    window.open(url, "_blank");
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <h1 className="text-xl font-black text-white flex items-center gap-2">
          <FileText className="w-5 h-5 text-red-500" />
          Offline Diagnostic Report Center
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Export tamper-evident, multi-format hardware intelligence reports directly from the encrypted Ghost Vault.
        </p>
      </div>

      {/* Target Selector Card */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
        <h3 className="text-sm font-bold text-white border-b border-zinc-800 pb-3">
          Select Diagnostic Target &amp; Session
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-zinc-400 uppercase tracking-wider mb-1.5">
              Machine Target
            </label>
            <select
              value={selectedMachine}
              onChange={(e) => setSelectedMachine(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-black border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500 font-mono"
            >
              {machines.map((m) => (
                <option key={m.machine_fingerprint} value={m.machine_fingerprint}>
                  {m.asset_tag ? `${m.asset_tag} (${m.machine_fingerprint.slice(0, 12)}...)` : m.machine_fingerprint.slice(0, 20)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-zinc-400 uppercase tracking-wider mb-1.5">
              Historical Scan Session
            </label>
            <select
              value={selectedScanId}
              onChange={(e) => setSelectedScanId(e.target.value)}
              disabled={scans.length === 0}
              className="w-full px-3.5 py-2.5 rounded-lg bg-black border border-zinc-800 text-xs text-white focus:outline-none focus:border-red-500 font-mono disabled:opacity-50"
            >
              {scans.length === 0 ? (
                <option>No scans available</option>
              ) : (
                scans.map((s) => (
                  <option key={s.scan_id} value={s.scan_id}>
                    {s.scan_id.slice(0, 8)} &bull; {new Date(s.timestamp_utc).toLocaleString()} ({s.platform} - Health {s.overall_health_score}/100)
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Export Options Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* PDF Exporter */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-red-600/70 transition shadow-xl">
          <div>
            <div className="p-3 rounded-xl bg-red-950/80 border border-red-700/60 text-red-500 w-fit mb-4 shadow-inner">
              <FileType className="w-6 h-6 text-red-500" />
            </div>
            <h4 className="text-sm font-bold text-white">Executive PDF Report</h4>
            <p className="text-xs text-zinc-400 mt-1">
              Formal multi-page document formatted with ReportLab tables, diagnostic scores, and security signature.
            </p>
          </div>
          <button
            onClick={() => handleDownload("pdf")}
            disabled={!selectedScanId}
            className="mt-5 w-full py-2.5 px-3 rounded-lg text-xs font-bold bg-red-600 hover:bg-red-500 text-white flex items-center justify-center gap-2 shadow-lg shadow-red-950/70 transition disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>

        {/* HTML Exporter */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-red-600/70 transition shadow-xl">
          <div>
            <div className="p-3 rounded-xl bg-red-950/80 border border-red-700/60 text-red-500 w-fit mb-4 shadow-inner">
              <Printer className="w-6 h-6 text-red-500" />
            </div>
            <h4 className="text-sm font-bold text-white">Self-Contained HTML</h4>
            <p className="text-xs text-zinc-400 mt-1">
              Interactive single-file report with stealth cyber theme and print stylesheet. Opens offline in any browser.
            </p>
          </div>
          <button
            onClick={() => handleDownload("html")}
            disabled={!selectedScanId}
            className="mt-5 w-full py-2.5 px-3 rounded-lg text-xs font-bold bg-red-600 hover:bg-red-500 text-white flex items-center justify-center gap-2 shadow-lg shadow-red-950/70 transition disabled:opacity-50 cursor-pointer"
          >
            <ExternalLink className="w-4 h-4" /> View / Download HTML
          </button>
        </div>

        {/* JSON Exporter */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-red-600/70 transition shadow-xl">
          <div>
            <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-700 text-white w-fit mb-4">
              <FileCode className="w-6 h-6 text-white" />
            </div>
            <h4 className="text-sm font-bold text-white">Canonical JSON Payload</h4>
            <p className="text-xs text-zinc-400 mt-1">
              Raw normalized v1.0.0 telemetry data for automated programmatic ingestion and cryptographic verification.
            </p>
          </div>
          <button
            onClick={() => handleDownload("json")}
            disabled={!selectedScanId}
            className="mt-5 w-full py-2.5 px-3 rounded-lg text-xs font-bold bg-zinc-900 hover:bg-zinc-800 text-white flex items-center justify-center gap-2 border border-zinc-700 transition disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-4 h-4" /> Download JSON
          </button>
        </div>

        {/* CSV Exporter */}
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-red-600/70 transition shadow-xl">
          <div>
            <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-700 text-white w-fit mb-4">
              <FileSpreadsheet className="w-6 h-6 text-white" />
            </div>
            <h4 className="text-sm font-bold text-white">Tabular CSV Spreadsheet</h4>
            <p className="text-xs text-zinc-400 mt-1">
              Detailed breakdown of diagnostic assertions, storage wear metrics, and component specs.
            </p>
          </div>
          <button
            onClick={() => handleDownload("csv")}
            disabled={!selectedScanId}
            className="mt-5 w-full py-2.5 px-3 rounded-lg text-xs font-bold bg-zinc-900 hover:bg-zinc-800 text-white flex items-center justify-center gap-2 border border-zinc-700 transition disabled:opacity-50 cursor-pointer"
          >
            <Download className="w-4 h-4" /> Download CSV
          </button>
        </div>
      </div>
    </div>
  );
};
