import React, { useEffect, useState } from "react";
import { api } from "./api";
import { Navbar } from "./components/Navbar";
import { VaultUnlockPage } from "./pages/VaultUnlockPage";
import { FleetOverviewPage } from "./pages/FleetOverviewPage";
import { MachineDetailPage } from "./pages/MachineDetailPage";
import { DiffViewerPage } from "./pages/DiffViewerPage";
import { DiagnosticsLabPage } from "./pages/DiagnosticsLabPage";
import { ReportCenterPage } from "./pages/ReportCenterPage";
import { AiCopilotPage } from "./pages/AiCopilotPage";
import { LogsPage } from "./pages/LogsPage";
import { DebugTreePage } from "./pages/DebugTreePage";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [selectedFingerprint, setSelectedFingerprint] = useState<string>("");
  const [isVaultUnlocked, setIsVaultUnlocked] = useState<boolean>(false);
  const [checkingVault, setCheckingVault] = useState<boolean>(true);
  const [sessionToken, setSessionToken] = useState<string>(api.getToken());

  // Check health and vault status
  const checkStatus = async () => {
    try {
      const health = await api.getHealth();
      setIsVaultUnlocked(health.vault_unlocked);
    } catch (e) {
      console.error("Health check error:", e);
    } finally {
      setCheckingVault(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleLockVault = async () => {
    try {
      await api.lockVault();
      setIsVaultUnlocked(false);
      setActiveTab("overview");
    } catch (e) {
      console.error("Error locking vault:", e);
    }
  };

  const handleSelectMachine = (fp: string) => {
    setSelectedFingerprint(fp);
    setActiveTab("machine-detail");
  };

  const handleOpenDiff = (fp: string) => {
    setSelectedFingerprint(fp);
    setActiveTab("diff");
  };

  const handleUpdateToken = (token: string) => {
    api.setToken(token);
    setSessionToken(token);
    checkStatus();
  };

  if (checkingVault) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-4 text-zinc-400 font-mono text-xs">
        <div className="w-16 h-16 relative">
          <div className="absolute inset-0 bg-red-600/30 blur-md rounded-full animate-ping" />
          <img src="/ghost-skull-red.png" alt="Booting Ghost-OS" className="w-full h-full object-contain relative z-10 drop-shadow-[0_0_12px_rgba(239,68,68,1)]" />
        </div>
        <div>
          <span className="text-red-500 mr-2 font-black">[GHOST-OS]</span> Initializing secure offline IPC bridge...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col font-sans selection:bg-red-950 selection:text-red-200">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isVaultUnlocked={isVaultUnlocked}
        onLockVault={handleLockVault}
        onOpenUnlockModal={() => setIsVaultUnlocked(false)}
        sessionToken={sessionToken}
        onUpdateToken={handleUpdateToken}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!isVaultUnlocked ? (
          <VaultUnlockPage onUnlocked={() => {
            setIsVaultUnlocked(true);
            checkStatus();
          }} />
        ) : (
          <>
            {activeTab === "overview" && (
              <FleetOverviewPage
                onSelectMachine={handleSelectMachine}
                onOpenDiff={handleOpenDiff}
              />
            )}
            {activeTab === "machines" && (
              <FleetOverviewPage
                onSelectMachine={handleSelectMachine}
                onOpenDiff={handleOpenDiff}
              />
            )}
            {activeTab === "machine-detail" && (
              <MachineDetailPage
                fingerprint={selectedFingerprint}
                onBack={() => setActiveTab("overview")}
                onOpenDiff={handleOpenDiff}
              />
            )}
            {activeTab === "diff" && (
              <DiffViewerPage initialFingerprint={selectedFingerprint} />
            )}
            {activeTab === "debug-tree" && <DebugTreePage />}
            {activeTab === "diagnostics" && <DiagnosticsLabPage />}
            {activeTab === "reports" && <ReportCenterPage />}
            {activeTab === "ai" && <AiCopilotPage />}
            {activeTab === "logs" && <LogsPage />}
          </>
        )}
      </main>

      <footer className="border-t border-zinc-900 bg-black py-4 text-center text-xs text-zinc-500 font-mono">
        <span className="text-white font-bold">GHOST-OS</span> <span className="text-red-500">v1.0.0</span> &bull; AUTHORITATIVE EXFAT PERSISTENCE &bull; ZERO HOST FOOTPRINT
      </footer>
    </div>
  );
};

export default App;

