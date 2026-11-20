import React, { useState, useEffect } from "react";
import {
  HardDrive,
  Cpu,
  GitCompare,
  Activity,
  FileText,
  Lock,
  Unlock,
  Key,
  Terminal,
  Bot,
  Power,
  Network,
} from "lucide-react";
import { api } from "../api";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isVaultUnlocked: boolean;
  onLockVault: () => void;
  onOpenUnlockModal: () => void;
  sessionToken: string;
  onUpdateToken: (token: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isVaultUnlocked,
  onLockVault,
  onOpenUnlockModal,
  sessionToken,
  onUpdateToken,
}) => {
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenInput, setTokenInput] = useState(sessionToken);

  // Terminate / Power-Off State
  const [showTerminateModal, setShowTerminateModal] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isPoweringOff, setIsPoweringOff] = useState(false);

  useEffect(() => {
    let timer: any = null;
    if (showTerminateModal && countdown !== null) {
      if (countdown > 0) {
        timer = setTimeout(() => {
          setCountdown(countdown - 1);
        }, 1000);
      } else if (countdown === 0 && !isPoweringOff) {
        setIsPoweringOff(true);
        api.terminateSystem(1).catch(() => {});
      }
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [showTerminateModal, countdown, isPoweringOff]);

  const handleCancelTerminate = () => {
    setShowTerminateModal(false);
    setCountdown(null);
    setIsPoweringOff(false);
  };

  const handleImmediateTerminate = async () => {
    setIsPoweringOff(true);
    setCountdown(0);
    try {
      await api.terminateSystem(1);
    } catch {
      // System shutting down
    }
  };

  const navItems = [
    { id: "overview", label: "Fleet Overview", icon: HardDrive },
    { id: "machines", label: "Registry", icon: Cpu },
    { id: "debug-tree", label: "DEBUG_TREE", icon: Network },
    { id: "diff", label: "Change Diff", icon: GitCompare },
    { id: "diagnostics", label: "Diagnostics Lab", icon: Activity },
    { id: "reports", label: "Report Center", icon: FileText },
    { id: "ai", label: "AI Copilot", icon: Bot },
    { id: "logs", label: "Audit Logs", icon: Terminal },
  ];

  return (
    <>
      <header className="bg-black/95 backdrop-blur-md border-b border-zinc-800 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-black border border-red-600/80 flex items-center justify-center shadow-lg shadow-red-950/80 p-1.5 relative overflow-hidden group">
              <div className="absolute inset-0 bg-red-600/20 blur-sm group-hover:bg-red-600/30 transition" />
              <img src="/ghost-skull-white.png" alt="Ghost-OS" className="w-full h-full object-contain relative z-10 drop-shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-black tracking-widest text-base text-white">GHOST-OS</span>
                <span className="text-[10px] uppercase font-black tracking-widest px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-700/80">
                  PORTABLE
                </span>
              </div>
              <span className="text-[10px] text-zinc-400 tracking-tight block">Zero-Footprint Hardware Intelligence</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? "bg-red-600 text-white shadow-md shadow-red-950/70 border border-red-500 font-bold"
                      : "text-zinc-400 hover:text-white hover:bg-zinc-900"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Right Status Controls */}
          <div className="flex items-center gap-3">
            {/* Vault Status Pill */}
            {isVaultUnlocked ? (
              <div className="flex items-center gap-1.5">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-950 border border-zinc-700 text-white text-xs font-mono font-bold">
                  <Unlock className="w-3.5 h-3.5 text-red-500" />
                  <span>VAULT: RAM ACTIVE</span>
                </div>
                <button
                  onClick={onLockVault}
                  title="Flush and Lock Vault"
                  className="p-1.5 rounded-lg bg-zinc-950 hover:bg-red-950/80 text-zinc-400 hover:text-red-400 border border-zinc-800 transition"
                >
                  <Lock className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenUnlockModal}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-950/90 border border-red-600 text-red-300 hover:bg-red-900 text-xs font-mono font-bold transition cursor-pointer shadow-sm shadow-red-950"
              >
                <Lock className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                <span>VAULT: LOCKED</span>
              </button>
            )}

            {/* Token Config Button */}
            <button
              onClick={() => setShowTokenModal(true)}
              title="Configure IPC Bearer Token"
              className="p-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800 transition"
            >
              <Key className="w-4 h-4" />
            </button>

            {/* DEBUG_TREE Button */}
            <button
              onClick={() => setActiveTab("debug-tree")}
              title="Open Multi-Node Type-C Hardware Topology & Sensor Bench"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold transition shadow-lg group cursor-pointer ${
                activeTab === "debug-tree"
                  ? "bg-red-600 text-white border-red-500 shadow-red-950/90"
                  : "bg-black hover:bg-zinc-900 text-red-400 hover:text-white border-red-600/70"
              }`}
            >
              <Network className="w-3.5 h-3.5 text-red-500 group-hover:scale-110 transition" />
              <span>DEBUG_TREE</span>
            </button>

            {/* Emergency Terminate Button */}
            <button
              onClick={() => {
                setShowTerminateModal(true);
                setCountdown(3);
                setIsPoweringOff(false);
              }}
              title="Emergency System Power-Off"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-950/90 hover:bg-red-900 border border-red-600 text-red-300 hover:text-white text-xs font-mono font-bold transition shadow-lg shadow-red-950/80 group cursor-pointer"
            >
              <Power className="w-3.5 h-3.5 text-red-500 group-hover:scale-110 transition" />
              <span>TERMINATE</span>
            </button>
          </div>
        </div>
      </header>

      {/* Session Token Modal */}
      {showTokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-black border border-red-600/70 rounded-xl max-w-md w-full p-6 shadow-2xl shadow-red-950/70">
            <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
              <Key className="w-4 h-4 text-red-500" />
              Ghost Localhost Bearer Token
            </h3>
            <p className="text-xs text-zinc-400 mb-4">
              Enter the bearer token printed in the Ghost-Core console to authorize IPC commands.
            </p>
            <input
              type="text"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="e.g. 32-character hex token"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-white font-mono text-xs focus:outline-none focus:border-red-500 mb-5"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowTokenModal(false)}
                className="px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-white rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onUpdateToken(tokenInput);
                  setShowTokenModal(false);
                }}
                className="px-4 py-2 text-xs font-bold text-white rounded-lg bg-red-600 hover:bg-red-500 transition shadow-lg shadow-red-950/60"
              >
                Save Token
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Terminate & Power-Off Modal with Pulsing Punisher Skull */}
      {showTerminateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xl p-4 animate-in fade-in duration-200">
          <div className="bg-black border-2 border-red-600 rounded-2xl max-w-md w-full p-8 shadow-[0_0_50px_rgba(239,68,68,0.4)] text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-700 via-red-500 to-red-700 animate-pulse" />

            {/* Glowing Pulsing Punisher Skull */}
            <div className="my-3 flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-red-600/30 blur-xl rounded-full animate-ping" />
                <img
                  src="/ghost-skull-red.png"
                  alt="Ghost Punisher Skull"
                  className="w-28 h-28 object-contain relative z-10 drop-shadow-[0_0_20px_rgba(239,68,68,0.95)] animate-pulse"
                />
              </div>
            </div>

            <h2 className="text-xl font-black text-white tracking-widest mt-2 uppercase font-mono">
              EMERGENCY SYSTEM TERMINATION
            </h2>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Flushing RAM Vault to USB, unmounting volumes safely, and powering off the host computer.
            </p>

            {/* Countdown Badge */}
            <div className="my-6 p-4 rounded-xl bg-zinc-950 border border-red-900/60 flex flex-col items-center justify-center">
              {isPoweringOff || countdown === 0 ? (
                <div className="text-red-500 font-mono font-black text-lg animate-pulse tracking-wider">
                  SHUTTING DOWN SYSTEM NOW...
                </div>
              ) : (
                <>
                  <div className="text-xs text-zinc-400 font-mono uppercase tracking-wider">POWER-OFF IN</div>
                  <div className="text-5xl font-mono font-black text-red-500 my-1 drop-shadow-[0_0_12px_rgba(239,68,68,0.8)]">
                    {countdown}
                  </div>
                  <div className="text-[11px] text-zinc-500 font-mono">SECONDS</div>
                </>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleCancelTerminate}
                disabled={isPoweringOff}
                className="px-5 py-2.5 text-xs font-bold text-zinc-300 hover:text-white rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 transition cursor-pointer"
              >
                ABORT TERMINATION
              </button>
              <button
                onClick={handleImmediateTerminate}
                disabled={isPoweringOff}
                className="px-5 py-2.5 text-xs font-black text-white rounded-xl bg-red-600 hover:bg-red-500 border border-red-500 transition shadow-lg shadow-red-950/80 cursor-pointer flex items-center gap-2"
              >
                <Power className="w-4 h-4" />
                POWER OFF NOW
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
