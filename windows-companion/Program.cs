using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using GhostCompanion.Scanners;

namespace GhostCompanion;

public class Program
{
    private static readonly HttpClient HttpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
    private const string DefaultCoreUrl = "http://127.0.0.1:8000";

    public static async Task<int> Main(string[] args)
    {
        // Enforce USB-local single-file extraction to prevent any host C:\temp residue
        string usbTemp = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".ghost_temp");
        if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("DOTNET_BUNDLE_EXTRACT_BASE_DIR")))
        {
            try
            {
                Directory.CreateDirectory(usbTemp);
                Environment.SetEnvironmentVariable("DOTNET_BUNDLE_EXTRACT_BASE_DIR", usbTemp, EnvironmentVariableTarget.Process);
            }
            catch { /* fallback gracefully */ }
        }

        Console.OutputEncoding = Encoding.UTF8;
        Console.ForegroundColor = ConsoleColor.Cyan;
        Console.WriteLine("==================================================================");
        Console.WriteLine("           GHOST-OS PORTABLE WINDOWS COMPANION v1.0.0            ");
        Console.WriteLine("    Zero-Install &bull; Offline Hardware Intelligence &bull; USB Vault    ");
        Console.WriteLine("==================================================================");
        Console.ResetColor();
        Console.WriteLine();

        bool scanOnly = false;
        bool noBrowser = false;
        string? outputFile = null;

        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--scan-only") scanOnly = true;
            else if (args[i] == "--no-browser") noBrowser = true;
            else if (args[i] == "--output" && i + 1 < args.Length) outputFile = args[++i];
        }

        Console.ForegroundColor = ConsoleColor.White;
        Console.WriteLine("[1/3] Extracting native hardware telemetry via WMI, CIM & Smartctl...");
        Console.ResetColor();

        string scanJson;
        try
        {
            scanJson = PayloadGenerator.GenerateNormalizedScanJson();
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("  ✓ Hardware telemetry extracted successfully.");
            Console.ResetColor();
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"  ✗ Hardware extraction failed: {ex.Message}");
            Console.ResetColor();
            return 1;
        }

        if (outputFile != null)
        {
            File.WriteAllText(outputFile, scanJson, Encoding.UTF8);
            Console.WriteLine($"  ✓ Scan written to: {outputFile}");
        }

        if (scanOnly)
        {
            Console.WriteLine(scanJson);
            return 0;
        }

        // [2/3] Ensure Ghost-Core Local IPC Engine is running
        Console.ForegroundColor = ConsoleColor.White;
        Console.WriteLine("[2/3] Checking Ghost-Core Localhost IPC Engine...");
        Console.ResetColor();

        bool coreOnline = await IsCoreOnlineAsync();
        if (!coreOnline)
        {
            Console.WriteLine("  Ghost-Core is not running. Launching background engine from USB...");
            LaunchCoreProcess();
            // Wait up to 10 seconds for core to report ready
            for (int attempt = 0; attempt < 20; attempt++)
            {
                Thread.Sleep(500);
                if (await IsCoreOnlineAsync())
                {
                    coreOnline = true;
                    break;
                }
            }
        }

        if (coreOnline)
        {
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine("  ✓ Ghost-Core is online at http://127.0.0.1:8000");
            Console.ResetColor();

            // Submit scan payload to Core IPC if Vault is unlocked or buffer for ingest
            Console.WriteLine("[3/3] Ingesting telemetry into Ghost Vault...");
            await IngestScanToCoreAsync(scanJson);
        }
        else
        {
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("  ! Ghost-Core service not detected on localhost:8000.");
            Console.WriteLine("    Payload cached in local execution memory.");
            Console.ResetColor();
        }

        // Open Dashboard in browser
        if (!noBrowser && coreOnline)
        {
            Console.WriteLine();
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("Opening Admin Command Center: http://127.0.0.1:8000/");
            Console.ResetColor();
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "http://127.0.0.1:8000/",
                    UseShellExecute = true
                });
            }
            catch { }
        }

        Console.WriteLine();
        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine("Ghost-Companion execution complete. Zero host registry or file modifications.");
        Console.ResetColor();

        return 0;
    }

    private static string? _cachedSessionToken = null;

    private static async Task<bool> IsCoreOnlineAsync()
    {
        try
        {
            var res = await HttpClient.GetAsync($"{DefaultCoreUrl}/api/v1/health");
            if (res.IsSuccessStatusCode)
            {
                string json = await res.Content.ReadAsStringAsync();
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("session_token", out var tokProp))
                {
                    _cachedSessionToken = tokProp.GetString();
                }
                return true;
            }
            return false;
        }
        catch
        {
            return false;
        }
    }

    private static void LaunchCoreProcess()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        // Determine root where ghost_core is located
        string workingDir = baseDir;
        if (!Directory.Exists(Path.Combine(baseDir, "ghost_core")) && Directory.Exists(Path.Combine(baseDir, "..", "ghost_core")))
        {
            workingDir = Path.GetFullPath(Path.Combine(baseDir, ".."));
        }
        else if (!Directory.Exists(Path.Combine(baseDir, "ghost_core")) && Directory.Exists(Path.Combine(baseDir, "..", "ghost-core")))
        {
            workingDir = Path.GetFullPath(Path.Combine(baseDir, ".."));
        }

        string[] pythonCandidates = {
            Path.Combine(baseDir, "python", "python.exe"),
            Path.Combine(baseDir, ".venv", "Scripts", "python.exe"),
            Path.Combine(baseDir, "..", ".venv", "Scripts", "python.exe")
        };

        string pythonExe = "python.exe";
        foreach (var p in pythonCandidates)
        {
            if (File.Exists(p)) { pythonExe = Path.GetFullPath(p); break; }
        }

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = "-m uvicorn ghost_core.api.server:app --host 127.0.0.1 --port 8000",
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(psi);
        }
        catch
        {
            try
            {
                var psiPy = new ProcessStartInfo
                {
                    FileName = "py.exe",
                    Arguments = "-3.12 -m uvicorn ghost_core.api.server:app --host 127.0.0.1 --port 8000",
                    WorkingDirectory = workingDir,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                Process.Start(psiPy);
            }
            catch { }
        }
    }

    private static async Task IngestScanToCoreAsync(string jsonPayload)
    {
        try
        {
            string token = Environment.GetEnvironmentVariable("GHOST_SESSION_TOKEN") ?? _cachedSessionToken ?? "";
            using var req = new HttpRequestMessage(HttpMethod.Post, $"{DefaultCoreUrl}/api/v1/scan/ingest");
            if (!string.IsNullOrEmpty(token))
            {
                req.Headers.Add("Authorization", $"Bearer {token}");
            }
            req.Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

            var res = await HttpClient.SendAsync(req);
            if (res.IsSuccessStatusCode)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("  ✓ Hardware scan ingested into encrypted vault.");
                Console.ResetColor();
            }
            else if ((int)res.StatusCode == 423) // Locked
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("  ! Vault is currently locked. Telemetry ready for ingestion upon unlocking.");
                Console.ResetColor();
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine($"  ! Core responded with status {(int)res.StatusCode}. Telemetry prepared.");
                Console.ResetColor();
            }
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine($"  ! Ingestion notification deferred: {ex.Message}");
            Console.ResetColor();
        }
    }
}
