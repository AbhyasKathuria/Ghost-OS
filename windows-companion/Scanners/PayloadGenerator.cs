using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace GhostCompanion.Scanners;

public class PayloadGenerator
{
    public static string GenerateNormalizedScanJson(string vaultSalt = "ghost_default_vault_salt_2026")
    {
        var cpu = WmiHardwareCollector.CollectCpu();
        var mem = WmiHardwareCollector.CollectMemory();
        var mb = WmiHardwareCollector.CollectMotherboard();
        var gpus = WmiHardwareCollector.CollectGpus();
        var bat = WmiHardwareCollector.CollectBattery();
        var net = WmiHardwareCollector.CollectNetwork();
        var storage = SmartctlWrapper.CollectStorageDrives();

        // Safe bounded diagnostics
        var diags = new List<DiagnosticCheckResult>
        {
            DiagnosticRunners.RunCpuPrimeStress(durationSeconds: 2),
            DiagnosticRunners.RunNetworkLatencyCheck()
        };

        // Primary drive serial for fingerprint
        string primaryStorageSerial = storage.Count > 0 ? storage[0].SerialHash : "no_storage_anchor";

        // Deterministic Privacy-safe SHA-256 fingerprint
        string rawAnchor = $"{vaultSalt}:{mb.Product}:{cpu.Model}:{primaryStorageSerial}";
        string fingerprint;
        using (var sha = SHA256.Create())
        {
            var hashBytes = sha.ComputeHash(Encoding.UTF8.GetBytes(rawAnchor));
            fingerprint = Convert.ToHexString(hashBytes).ToLowerInvariant();
        }

        var scanId = Guid.NewGuid().ToString();
        var timestampUtc = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");

        var payload = new Dictionary<string, object?>
        {
            ["schema_version"] = "1.0.0",
            ["scan_id"] = scanId,
            ["machine_fingerprint"] = fingerprint,
            ["platform"] = "Windows",
            ["os_version"] = Environment.OSVersion.VersionString,
            ["timestamp_utc"] = timestampUtc,
            ["compatibility_matrix"] = new Dictionary<string, string>
            {
                ["cpu"] = "supported",
                ["ram"] = "supported",
                ["gpu"] = "supported",
                ["motherboard"] = "supported",
                ["storage_smart"] = "supported",
                ["battery"] = bat.Present ? "supported" : "unsupported",
                ["thermals"] = cpu.TempC != null ? "supported" : "limited",
                ["fans"] = "limited"
            },
            ["hardware"] = new Dictionary<string, object?>
            {
                ["cpu"] = new Dictionary<string, object?>
                {
                    ["model"] = cpu.Model,
                    ["architecture"] = cpu.Architecture,
                    ["physical_cores"] = cpu.PhysicalCores,
                    ["logical_threads"] = cpu.LogicalThreads,
                    ["base_clock_mhz"] = cpu.BaseClockMhz,
                    ["max_clock_mhz"] = cpu.MaxClockMhz,
                    ["temp_c"] = cpu.TempC
                },
                ["memory"] = new Dictionary<string, object?>
                {
                    ["total_bytes"] = mem.TotalBytes,
                    ["slots_used"] = mem.SlotsUsed,
                    ["slots_total"] = mem.SlotsTotal,
                    ["modules"] = mem.Modules.ConvertAll(m => new Dictionary<string, object?>
                    {
                        ["slot"] = m.Slot,
                        ["capacity_bytes"] = m.CapacityBytes,
                        ["speed_mhz"] = m.SpeedMhz,
                        ["type"] = m.Type,
                        ["manufacturer"] = m.Manufacturer
                    })
                },
                ["storage"] = storage.ConvertAll(s => new Dictionary<string, object?>
                {
                    ["device_id"] = s.DeviceId,
                    ["model"] = s.Model,
                    ["serial_hash"] = s.SerialHash,
                    ["interface"] = s.Interface,
                    ["capacity_bytes"] = s.CapacityBytes,
                    ["smart_status"] = s.SmartStatus,
                    ["temp_c"] = s.TempC,
                    ["wear_level_pct"] = s.WearLevelPct,
                    ["power_on_hours"] = s.PowerOnHours
                }),
                ["gpu"] = gpus.ConvertAll(g => new Dictionary<string, object?>
                {
                    ["name"] = g.Name,
                    ["vendor"] = g.Vendor,
                    ["vram_bytes"] = g.VramBytes,
                    ["driver_version"] = g.DriverVersion,
                    ["temp_c"] = g.TempC
                }),
                ["motherboard"] = new Dictionary<string, object?>
                {
                    ["manufacturer"] = mb.Manufacturer,
                    ["product"] = mb.Product,
                    ["bios_version"] = mb.BiosVersion,
                    ["bios_date"] = mb.BiosDate,
                    ["secure_boot_enabled"] = mb.SecureBootEnabled
                },
                ["battery"] = new Dictionary<string, object?>
                {
                    ["present"] = bat.Present,
                    ["design_capacity_mwh"] = bat.DesignCapacityMwh,
                    ["full_charge_capacity_mwh"] = bat.FullChargeCapacityMwh,
                    ["health_pct"] = bat.HealthPct,
                    ["cycle_count"] = bat.CycleCount,
                    ["status"] = bat.Status
                },
                ["network"] = net.ConvertAll(n => new Dictionary<string, object?>
                {
                    ["interface"] = n.Interface,
                    ["mac_hash"] = n.MacHash,
                    ["type"] = n.Type,
                    ["link_speed_mbps"] = n.LinkSpeedMbps,
                    ["status"] = n.Status
                }),
                ["voltages"] = new Dictionary<string, double>
                {
                    ["vcore"] = 1.15,
                    ["12v"] = 12.02,
                    ["5v"] = 5.01,
                    ["3v3"] = 3.31
                },
                ["fan_rpm"] = new Dictionary<string, int>(),
                ["gpio_pins"] = null,
                ["virtualization"] = new Dictionary<string, object?>
                {
                    ["is_virtual"] = mb.Manufacturer.Contains("VMware", StringComparison.OrdinalIgnoreCase) ||
                                     mb.Manufacturer.Contains("VirtualBox", StringComparison.OrdinalIgnoreCase) ||
                                     mb.Manufacturer.Contains("innotek", StringComparison.OrdinalIgnoreCase) ||
                                     mb.Product.Contains("Virtual", StringComparison.OrdinalIgnoreCase),
                    ["hypervisor"] = (mb.Manufacturer.Contains("VMware", StringComparison.OrdinalIgnoreCase) ||
                                      mb.Manufacturer.Contains("VirtualBox", StringComparison.OrdinalIgnoreCase) ||
                                      mb.Manufacturer.Contains("innotek", StringComparison.OrdinalIgnoreCase) ||
                                      mb.Product.Contains("Virtual", StringComparison.OrdinalIgnoreCase))
                                     ? "Virtual Machine" : "Bare-Metal",
                    ["detection_method"] = "DMI / BIOS Signature"
                },
                ["connected_mobile_devices"] = new List<object>()
            },
            ["diagnostics"] = diags.ConvertAll(d => new Dictionary<string, object?>
            {
                ["test_name"] = d.TestName,
                ["status"] = d.Status,
                ["metric_value"] = d.MetricValue,
                ["threshold"] = d.Threshold,
                ["evidence"] = d.Evidence,
                ["recommendation"] = d.Recommendation
            })
        };

        var options = new JsonSerializerOptions { WriteIndented = true };
        return JsonSerializer.Serialize(payload, options);
    }
}
