// Canonical TypeScript Interfaces for Ghost-OS Admin Dashboard

export type DiagnosticStatus = "PASS" | "WARN" | "FAIL";
export type PlatformType = "Windows" | "Linux" | "macOS";
export type ModuleCompatibility = "supported" | "limited" | "unsupported" | "permission_denied";

export interface CpuSpec {
  model: string;
  architecture: string;
  physical_cores: number;
  logical_threads: number;
  base_clock_mhz?: number;
  max_clock_mhz?: number;
  temp_c?: number;
}

export interface MemoryModule {
  slot: string;
  capacity_bytes: number;
  speed_mhz?: number;
  type?: string;
  manufacturer?: string;
}

export interface MemorySpec {
  total_bytes: number;
  slots_used: number;
  slots_total: number;
  modules: MemoryModule[];
}

export interface StorageDevice {
  device_id: string;
  model: string;
  serial_hash: string;
  interface: string;
  capacity_bytes: number;
  smart_status: string;
  temp_c?: number;
  wear_level_pct?: number;
  power_on_hours?: number;
}

export interface GpuSpec {
  name: string;
  vendor: string;
  vram_bytes?: number;
  driver_version?: string;
  temp_c?: number;
}

export interface MotherboardSpec {
  manufacturer: string;
  product: string;
  bios_version: string;
  bios_date?: string;
  secure_boot_enabled?: boolean;
}

export interface BatterySpec {
  present: boolean;
  design_capacity_mwh?: number;
  full_charge_capacity_mwh?: number;
  health_pct?: number;
  cycle_count?: number;
  status?: string;
}

export interface NetworkInterface {
  interface: string;
  mac_hash: string;
  type: string;
  link_speed_mbps?: number;
  status: string;
}

export interface ConnectedPeripheralSpec {
  category: string;
  name: string;
  connection_type: string;
  status: string;
  details?: Record<string, any>;
}

export interface MobileDeviceSpec {
  device_type: string;
  model: string;
  os_version: string;
  serial_hash: string;
  battery_health_pct?: number;
  battery_cycles?: number;
  status: string;
  motherboard_model?: string;
  soc_chipset?: string;
  firmware_version?: string;
  storage_capacity_bytes?: number;
  storage_wear_pct?: number;
  ram_bytes?: number;
  battery_wear_pct?: number;
  battery_design_mwh?: number;
  battery_full_mwh?: number;
  temperatures_c?: Record<string, number>;
  voltages?: Record<string, number>;
}

export interface HardwareSpec {
  cpu: CpuSpec;
  memory: MemorySpec;
  storage: StorageDevice[];
  gpu: GpuSpec[];
  motherboard: MotherboardSpec;
  battery: BatterySpec;
  network: NetworkInterface[];
  voltages?: Record<string, number>;
  fan_rpm?: Record<string, number>;
  connected_peripherals?: ConnectedPeripheralSpec[];
  connected_mobile_devices?: MobileDeviceSpec[];
}

export interface DiagnosticResult {
  test_name: string;
  status: DiagnosticStatus;
  metric_value?: number;
  threshold?: number;
  evidence: string;
  recommendation: string;
}

export interface NormalizedScanPayload {
  schema_version: string;
  scan_id: string;
  machine_fingerprint: string;
  platform: PlatformType;
  os_version: string;
  timestamp_utc: string;
  compatibility_matrix: Record<string, ModuleCompatibility>;
  hardware: HardwareSpec;
  diagnostics: DiagnosticResult[];
}

export interface HealthScores {
  overall_score: number;
  cpu_score: number;
  ram_score: number;
  storage_score: number;
  battery_score: number;
  thermal_score: number;
  summary: string;
}

export interface MachineSummary {
  machine_fingerprint: string;
  first_seen_utc: string;
  last_seen_utc: string;
  asset_tag?: string;
  notes?: string;
  scan_count: number;
  latest_health_score?: number;
  latest_scan_utc?: string;
}

export interface ScanSessionDetail {
  scan_id: string;
  machine_fingerprint: string;
  platform: PlatformType;
  os_version: string;
  timestamp_utc: string;
  overall_health_score: number;
  raw_payload: NormalizedScanPayload;
  health_scores?: HealthScores;
  diagnostics: DiagnosticResult[];
}

export interface ComponentChange {
  component: string;
  change_type: "UPGRADE" | "REPLACEMENT" | "DEGRADATION" | "FIRMWARE_CONFIG" | "REMOVAL" | "INFO";
  property_name: string;
  old_value: any;
  new_value: any;
  description: string;
}

export interface HardwareDiffReport {
  machine_fingerprint: string;
  baseline_scan_id: string;
  current_scan_id: string;
  baseline_timestamp_utc: string;
  current_timestamp_utc: string;
  baseline_platform: string;
  current_platform: string;
  changes_detected: boolean;
  total_changes: number;
  changes: ComponentChange[];
  degradations: ComponentChange[];
  summary: string;
}

export interface MaintenanceRecord {
  id: number;
  machine_fingerprint: string;
  timestamp_utc: string;
  technician_name: string;
  action_type: string;
  notes: string;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  timestamp_utc: string;
  details: string;
}
