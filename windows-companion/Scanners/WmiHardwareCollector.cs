using System;
using System.Collections.Generic;
using System.IO;
using System.Management;
using System.Security.Cryptography;
using System.Text;

namespace GhostCompanion.Scanners;

public record CpuData(
    string Model,
    string Architecture,
    int PhysicalCores,
    int LogicalThreads,
    double? BaseClockMhz,
    double? MaxClockMhz,
    double? TempC
);

public record MemoryModuleData(
    string Slot,
    long CapacityBytes,
    int? SpeedMhz,
    string? Type,
    string? Manufacturer
);

public record MemoryData(
    long TotalBytes,
    int SlotsUsed,
    int SlotsTotal,
    List<MemoryModuleData> Modules
);

public record GpuData(
    string Name,
    string Vendor,
    long? VramBytes,
    string? DriverVersion,
    double? TempC
);

public record MotherboardData(
    string Manufacturer,
    string Product,
    string BiosVersion,
    string? BiosDate,
    bool? SecureBootEnabled
);

public record BatteryData(
    bool Present,
    double? DesignCapacityMwh,
    double? FullChargeCapacityMwh,
    double? HealthPct,
    int? CycleCount,
    string? Status
);

public record NetworkData(
    string Interface,
    string MacHash,
    string Type,
    int? LinkSpeedMbps,
    string Status
);

public static class WmiHardwareCollector
{
    public static string ComputeSha256(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return "unknown_hash";
        using var sha = SHA256.Create();
        var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(raw.Trim()));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    public static CpuData CollectCpu()
    {
        string model = "Generic x86_64 Processor";
        string arch = "x86_64";
        int cores = Environment.ProcessorCount > 1 ? Environment.ProcessorCount / 2 : 1;
        int threads = Environment.ProcessorCount;
        double? maxClock = null;
        double? curClock = null;
        double? temp = null;

        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_Processor");
            foreach (ManagementObject obj in searcher.Get())
            {
                model = obj["Name"]?.ToString()?.Trim() ?? model;
                cores = Convert.ToInt32(obj["NumberOfCores"] ?? cores);
                threads = Convert.ToInt32(obj["NumberOfLogicalProcessors"] ?? threads);
                maxClock = Convert.ToDouble(obj["MaxClockSpeed"] ?? 0);
                curClock = Convert.ToDouble(obj["CurrentClockSpeed"] ?? 0);
                break;
            }
        }
        catch { }

        // Attempt thermal reading via MSAcpi_ThermalZoneTemperature if permitted
        try
        {
            using var thermalSearcher = new ManagementObjectSearcher(@"root\WMI", "SELECT * FROM MSAcpi_ThermalZoneTemperature");
            foreach (ManagementObject obj in thermalSearcher.Get())
            {
                long rawK = Convert.ToInt64(obj["CurrentTemperature"]);
                // MSAcpi reports in tenths of Kelvin: (raw - 2732) / 10 = Celsius
                double c = (rawK - 2732) / 10.0;
                if (c > 0 && c < 125)
                {
                    temp = Math.Round(c, 1);
                    break;
                }
            }
        }
        catch { }

        return new CpuData(model, arch, cores, threads, curClock, maxClock, temp);
    }

    public static MemoryData CollectMemory()
    {
        long totalBytes = 0;
        int slotsTotal = 0;
        var modules = new List<MemoryModuleData>();

        try
        {
            using var memArraySearcher = new ManagementObjectSearcher("SELECT * FROM Win32_PhysicalMemoryArray");
            foreach (ManagementObject obj in memArraySearcher.Get())
            {
                slotsTotal += Convert.ToInt32(obj["MemoryDevices"] ?? 0);
            }
        }
        catch { }

        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_PhysicalMemory");
            foreach (ManagementObject obj in searcher.Get())
            {
                string slot = obj["DeviceLocator"]?.ToString() ?? obj["BankLabel"]?.ToString() ?? $"Slot{modules.Count}";
                long cap = Convert.ToInt64(obj["Capacity"] ?? 0);
                int? speed = obj["Speed"] != null ? Convert.ToInt32(obj["Speed"]) : null;
                string mfg = obj["Manufacturer"]?.ToString()?.Trim();
                int memTypeCode = Convert.ToInt32(obj["SMBIOSMemoryType"] ?? obj["MemoryType"] ?? 0);
                string memType = DecodeSmbiosMemoryType(memTypeCode);

                totalBytes += cap;
                modules.Add(new MemoryModuleData(slot, cap, speed, memType, mfg));
            }
        }
        catch { }

        if (slotsTotal < modules.Count) slotsTotal = modules.Count;

        return new MemoryData(totalBytes, modules.Count, slotsTotal, modules);
    }

    private static string DecodeSmbiosMemoryType(int code)
    {
        return code switch
        {
            24 => "DDR3",
            26 => "DDR4",
            30 => "LPDDR4",
            34 => "DDR5",
            35 => "LPDDR5",
            _ => "DDR"
        };
    }

    public static MotherboardData CollectMotherboard()
    {
        string mfg = "Generic Motherboard";
        string prod = "Desktop/Notebook";
        string biosVer = "1.0.0";
        string? biosDate = null;
        bool? secureBoot = null;

        try
        {
            using var mbSearcher = new ManagementObjectSearcher("SELECT * FROM Win32_BaseBoard");
            foreach (ManagementObject obj in mbSearcher.Get())
            {
                mfg = obj["Manufacturer"]?.ToString()?.Trim() ?? mfg;
                prod = obj["Product"]?.ToString()?.Trim() ?? prod;
                break;
            }
        }
        catch { }

        try
        {
            using var biosSearcher = new ManagementObjectSearcher("SELECT * FROM Win32_BIOS");
            foreach (ManagementObject obj in biosSearcher.Get())
            {
                biosVer = obj["SMBIOSBIOSVersion"]?.ToString()?.Trim() ?? biosVer;
                biosDate = obj["ReleaseDate"]?.ToString();
                break;
            }
        }
        catch { }

        // Check Secure Boot status
        try
        {
            using var key = Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Control\SecureBoot\State");
            if (key != null)
            {
                int val = Convert.ToInt32(key.GetValue("UEFISecureBootEnabled", 0));
                secureBoot = (val == 1);
            }
        }
        catch { }

        return new MotherboardData(mfg, prod, biosVer, biosDate, secureBoot);
    }

    public static List<GpuData> CollectGpus()
    {
        var gpus = new List<GpuData>();
        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_VideoController");
            foreach (ManagementObject obj in searcher.Get())
            {
                string name = obj["Name"]?.ToString()?.Trim() ?? "Display Adapter";
                long vram = Convert.ToInt64(obj["AdapterRAM"] ?? 0);
                string drv = obj["DriverVersion"]?.ToString()?.Trim();

                string vendor = "Unknown";
                if (name.Contains("NVIDIA", StringComparison.OrdinalIgnoreCase)) vendor = "NVIDIA";
                else if (name.Contains("AMD", StringComparison.OrdinalIgnoreCase) || name.Contains("Radeon", StringComparison.OrdinalIgnoreCase)) vendor = "AMD";
                else if (name.Contains("Intel", StringComparison.OrdinalIgnoreCase)) vendor = "Intel";

                gpus.Add(new GpuData(name, vendor, vram > 0 ? vram : null, drv, null));
            }
        }
        catch { }

        return gpus;
    }

    public static BatteryData CollectBattery()
    {
        bool present = false;
        double? designCap = null;
        double? fullCap = null;
        double? health = null;
        int? cycles = null;
        string? status = null;

        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_Battery");
            foreach (ManagementObject obj in searcher.Get())
            {
                present = true;
                designCap = obj["DesignCapacity"] != null ? Convert.ToDouble(obj["DesignCapacity"]) : null;
                fullCap = obj["FullChargeCapacity"] != null ? Convert.ToDouble(obj["FullChargeCapacity"]) : null;
                int estCharge = Convert.ToInt32(obj["EstimatedChargeRemaining"] ?? 0);
                status = estCharge > 0 ? $"Remaining {estCharge}%" : "Discharging";

                if (designCap > 0 && fullCap > 0)
                {
                    health = Math.Round((fullCap.Value / designCap.Value) * 100, 1);
                }
                break;
            }
        }
        catch { }

        return new BatteryData(present, designCap, fullCap, health, cycles, status);
    }

    public static List<NetworkData> CollectNetwork()
    {
        var list = new List<NetworkData>();
        try
        {
            using var searcher = new ManagementObjectSearcher("SELECT * FROM Win32_NetworkAdapter WHERE NetConnectionStatus = 2 OR PhysicalAdapter = True");
            foreach (ManagementObject obj in searcher.Get())
            {
                string name = obj["Name"]?.ToString()?.Trim() ?? "Network Adapter";
                string mac = obj["MACAddress"]?.ToString()?.Trim() ?? "";
                string type = obj["AdapterType"]?.ToString() ?? "Ethernet";
                int speed = obj["Speed"] != null ? (int)(Convert.ToInt64(obj["Speed"]) / 1_000_000) : 0;
                int connStatus = Convert.ToInt32(obj["NetConnectionStatus"] ?? 0);

                if (string.IsNullOrEmpty(mac)) continue;

                list.Add(new NetworkData(
                    name,
                    ComputeSha256(mac),
                    name.Contains("Wi-Fi", StringComparison.OrdinalIgnoreCase) || name.Contains("Wireless", StringComparison.OrdinalIgnoreCase) ? "Wireless" : type,
                    speed > 0 ? speed : null,
                    connStatus == 2 ? "Connected" : "Disconnected"
                ));
            }
        }
        catch { }

        return list;
    }
}
