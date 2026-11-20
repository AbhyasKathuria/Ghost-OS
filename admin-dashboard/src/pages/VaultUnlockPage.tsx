import React, { useState } from "react";
import { Eye, EyeOff, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "../api";

interface VaultUnlockPageProps {
  onUnlocked: () => void;
}

export const VaultUnlockPage: React.FC<VaultUnlockPageProps> = ({ onUnlocked }) => {
  const [mode, setMode] = useState<"password" | "recovery" | "create">("password");
  const [password, setPassword] = useState("");
  const [recoveryKey, setRecoveryKey] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Rate-limiting simulation
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  React.useEffect(() => {
    api.getHealth().then((h) => {
      if (h.vault_exists === false) {
        setMode("create");
      }
    }).catch(() => {});
  }, []);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cooldownSeconds > 0) return;

    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const secret = mode === "password" ? password : recoveryKey;
      await api.unlockVault(secret);
      setSuccessMsg("Vault unlocked into memory.");
      setFailedAttempts(0);
      setTimeout(() => onUnlocked(), 600);
    } catch (err: any) {
      const newAttempts = failedAttempts + 1;
      setFailedAttempts(newAttempts);
      setError(err.message || "Failed to unlock vault.");

      // Rate limiting: 3+ failures triggers 10 second cooldown
      if (newAttempts >= 3) {
        setCooldownSeconds(10);
        const timer = setInterval(() => {
          setCooldownSeconds((prev) => {
            if (prev <= 1) {
              clearInterval(timer);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateVault = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await api.createVault(password);
      setSuccessMsg(`Vault created! Emergency recovery key: ${res.recovery_key}`);
      setTimeout(() => onUnlocked(), 2500);
    } catch (err: any) {
      setError(err.message || "Failed to create vault.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-black border border-red-600/70 rounded-2xl p-8 shadow-2xl shadow-red-950/70 relative overflow-hidden">
        {/* Decorative Top Accent */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-red-700 via-red-500 to-red-700" />

        <div className="text-center mb-6">
          <div className="w-20 h-20 rounded-2xl bg-black border border-red-600/90 text-red-500 mx-auto flex items-center justify-center mb-3 shadow-2xl shadow-red-950/90 p-2.5 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-t from-red-950/80 via-transparent to-red-950/40" />
            <img src="/ghost-skull-white.png" alt="Ghost-OS Logo" className="w-full h-full object-contain relative z-10 drop-shadow-[0_0_10px_rgba(239,68,68,0.9)] animate-pulse" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-wider">Ghost Vault Authentication</h2>
          <p className="text-xs text-zinc-400 mt-1 font-mono">
            Zero-Footprint In-Memory SQLite Decryption
          </p>
        </div>

        {/* Tab Selection */}
        <div className="grid grid-cols-3 gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800 mb-6 text-xs font-semibold">
          <button
            onClick={() => {
              setMode("password");
              setError(null);
            }}
            className={`py-2 rounded-md transition font-bold ${
              mode === "password"
                ? "bg-red-600 text-white shadow-md shadow-red-950"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Password
          </button>
          <button
            onClick={() => {
              setMode("recovery");
              setError(null);
            }}
            className={`py-2 rounded-md transition font-bold ${
              mode === "recovery"
                ? "bg-red-600 text-white shadow-md shadow-red-950"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            Recovery Key
          </button>
          <button
            onClick={() => {
              setMode("create");
              setError(null);
            }}
            className={`py-2 rounded-md transition font-bold ${
              mode === "create"
                ? "bg-red-600 text-white shadow-md shadow-red-950"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`}
          >
            New Vault
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/80 border border-red-600 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-lg bg-zinc-900 border border-zinc-700 text-white text-xs flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
            <span className="font-mono break-all">{successMsg}</span>
          </div>
        )}

        {cooldownSeconds > 0 && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/90 border border-red-500 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-400 animate-pulse" />
            <span>Rate-limit active: Retry in {cooldownSeconds}s</span>
          </div>
        )}

        {mode !== "create" ? (
          <form onSubmit={handleUnlock} className="space-y-4">
            {mode === "password" ? (
              <div>
                <label className="block text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2">
                  Technician Master Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="Enter password..."
                    disabled={cooldownSeconds > 0 || loading}
                    className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-white text-sm focus:outline-none focus:border-red-500 disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-zinc-500 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2">
                  Emergency Recovery Key
                </label>
                <input
                  type="text"
                  value={recoveryKey}
                  onChange={(e) => setRecoveryKey(e.target.value)}
                  required
                  placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                  disabled={cooldownSeconds > 0 || loading}
                  className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-white font-mono text-xs focus:outline-none focus:border-red-500 disabled:opacity-50"
                />
                <p className="text-[11px] text-zinc-400 mt-1.5">
                  Located in <span className="font-mono text-white">recovery_key.txt</span> on USB root.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || cooldownSeconds > 0}
              className="w-full py-3 rounded-lg font-black text-xs uppercase tracking-wider bg-red-600 hover:bg-red-500 text-white shadow-xl shadow-red-950/80 transition disabled:opacity-50 cursor-pointer"
            >
              {loading ? "Hydrating Database..." : "Decrypt & Unlock Vault"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleCreateVault} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-zinc-300 uppercase tracking-wider mb-2">
                Set Vault Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Choose a strong password..."
                disabled={loading}
                className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-white text-sm focus:outline-none focus:border-red-500"
              />
              <p className="text-[11px] text-zinc-400 mt-1.5">
                Initializes <span className="font-mono text-white">vault.enc</span> on the exFAT USB partition.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || !password}
              className="w-full py-3 rounded-lg font-bold text-xs uppercase tracking-wider bg-red-600 hover:bg-red-500 text-white shadow-xl shadow-red-950/80 transition disabled:opacity-50 cursor-pointer"
            >
              {loading ? "Initializing..." : "Create New Vault"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
