import React, { useEffect, useState } from "react";
import { Terminal, RefreshCw } from "lucide-react";
import { api } from "../api";
import type { AuditEvent } from "../types";

export const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await api.listAuditEvents(100);
      setLogs(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 flex items-center justify-between shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div>
          <h1 className="text-xl font-black text-white flex items-center gap-2">
            <Terminal className="w-5 h-5 text-red-500" />
            Security &amp; Operational Audit Trail
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Cryptographic and diagnostic audit events persisted permanently in Ghost Vault.
          </p>
        </div>
        <button
          onClick={fetchLogs}
          className="p-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800 transition cursor-pointer"
          title="Refresh Logs"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
              <tr>
                <th className="py-3 px-4 font-bold">Event ID</th>
                <th className="py-3 px-4 font-bold">Action Classification</th>
                <th className="py-3 px-4 font-bold">Audit Details &amp; Anchor</th>
                <th className="py-3 px-4 font-bold text-right">Timestamp UTC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/80">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-zinc-500 font-mono">
                    No audit records recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((e) => (
                  <tr key={e.id} className="hover:bg-zinc-900/60 transition">
                    <td className="py-3 px-4 font-mono text-zinc-500 font-bold">#{e.id}</td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] font-bold text-red-400 bg-red-950/80 px-2 py-0.5 rounded border border-red-700/60 uppercase">
                        {e.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-300 font-mono text-[11px]">{e.details}</td>
                    <td className="py-3 px-4 text-zinc-400 text-right font-mono text-[11px]">
                      {new Date(e.timestamp_utc).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
