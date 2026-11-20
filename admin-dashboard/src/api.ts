// Ghost-OS Local API Client

import type {
  AuditEvent,
  HardwareDiffReport,
  MachineSummary,
  MaintenanceRecord,
  NormalizedScanPayload,
  ScanSessionDetail,
} from "./types";

const API_BASE = "/api/v1";

class GhostApiClient {
  private token: string = localStorage.getItem("ghost_session_token") || "";

  public setToken(token: string) {
    this.token = token.trim();
    localStorage.setItem("ghost_session_token", this.token);
  }

  public getToken(): string {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    if (this.token) {
      headers.set("Authorization", `Bearer ${this.token}`);
    }
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      if (res.status === 401) {
        this.token = "";
        localStorage.removeItem("ghost_session_token");
      }
      let errorMsg = `API Error ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) errorMsg = errorJson.detail;
      } catch {
        // ignore fallback
      }
      const err = new Error(errorMsg);
      (err as any).status = res.status;
      throw err;
    }

    return res.json();
  }

  public async getHealth(): Promise<{
    status: string;
    engine: string;
    version: string;
    vault_unlocked: boolean;
    vault_path: string;
    vault_exists?: boolean;
    session_token?: string;
  }> {
    const res = await this.request<{
      status: string;
      engine: string;
      version: string;
      vault_unlocked: boolean;
      vault_path: string;
      vault_exists?: boolean;
      session_token?: string;
    }>("/health");
    if (res.session_token) {
      this.setToken(res.session_token);
    }
    return res;
  }

  public async unlockVault(secret: string, vaultPath?: string): Promise<{ status: string; message: string }> {
    return this.request("/vault/unlock", {
      method: "POST",
      body: JSON.stringify({ secret, vault_path: vaultPath }),
    });
  }

  public async createVault(password: string, recoveryKey?: string, vaultPath?: string): Promise<{
    status: string;
    vault_path: string;
    recovery_key: string;
    message: string;
  }> {
    return this.request("/vault/create", {
      method: "POST",
      body: JSON.stringify({ password, recovery_key: recoveryKey, vault_path: vaultPath }),
    });
  }

  public async lockVault(): Promise<{ status: string; message: string }> {
    return this.request("/vault/lock", {
      method: "POST",
    });
  }

  public async listMachines(query?: string): Promise<MachineSummary[]> {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    return this.request(`/machines${q}`);
  }

  public async getMachine(fingerprint: string): Promise<{
    machine: MachineSummary;
    latest_scan?: ScanSessionDetail;
    scan_history: any[];
    maintenance_records: MaintenanceRecord[];
  }> {
    return this.request(`/machines/${fingerprint}`);
  }

  public async getMachineDiff(fingerprint: string, scan1?: string, scan2?: string): Promise<HardwareDiffReport> {
    const params = new URLSearchParams();
    if (scan1) params.append("scan1", scan1);
    if (scan2) params.append("scan2", scan2);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.request(`/machines/${fingerprint}/diff${qs}`);
  }

  public async getScan(scanId: string): Promise<ScanSessionDetail> {
    return this.request(`/scans/${scanId}`);
  }

  public async ingestScan(payload: NormalizedScanPayload): Promise<{
    scan_id: string;
    overall_health_score: number;
    health_summary: string;
    score_breakdown: any;
    diff_report?: any;
  }> {
    return this.request("/scan/ingest", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  public async addMaintenance(
    fingerprint: string,
    actionType: string,
    technicianName: string,
    notes: string,
  ): Promise<{ status: string; record_id: number }> {
    return this.request(`/machines/${fingerprint}/maintenance`, {
      method: "POST",
      body: JSON.stringify({
        action_type: actionType,
        technician_name: technicianName,
        notes,
      }),
    });
  }

  public async listAuditEvents(limit = 100): Promise<AuditEvent[]> {
    return this.request(`/audit?limit=${limit}`);
  }

  public async getAiStatus(): Promise<{
    is_gguf_active: boolean;
    model_name: string | null;
    fallback_engine: string;
    models_dir: string;
  }> {
    return this.request("/ai/status");
  }

  public async chatWithAi(
    message: string,
    machineFingerprint?: string,
  ): Promise<{
    reply: string;
    sources: string[];
    engine_used: string;
    model_name?: string | null;
  }> {
    return this.request("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message, machine_fingerprint: machineFingerprint }),
    });
  }

  public getExportUrl(scanId: string, format: "html" | "pdf" | "json" | "csv"): string {
    return `${API_BASE}/reports/${scanId}/export?format=${format}`;
  }

  public async terminateSystem(delaySeconds = 3): Promise<{ status: string; message: string; countdown_seconds: number }> {
    return this.request("/system/terminate", {
      method: "POST",
      body: JSON.stringify({ delay_seconds: delaySeconds, flush_vault: true }),
    });
  }

  public async getDebugTree(): Promise<any> {
    return this.request("/debug-tree");
  }

  public async runDebugTree(): Promise<any> {
    return this.request("/debug-tree/run", {
      method: "POST",
    });
  }

  public async testCameraSensor(duration = 3): Promise<any> {
    return this.request("/sensors/test-camera", {
      method: "POST",
      body: JSON.stringify({ duration }),
    });
  }

  public async testMicrophoneSensor(duration = 3): Promise<any> {
    return this.request("/sensors/test-microphone", {
      method: "POST",
      body: JSON.stringify({ duration }),
    });
  }
}

export const api = new GhostApiClient();
