<#
.SYNOPSIS
    Automated USB Staging & Deployment Script for Ghost-OS.
.DESCRIPTION
    Initializes a 128GB USB flash drive with the GhostVault exFAT partition,
    creates the standard directory hierarchy, and deploys the portable Ghost-OS binaries.
.PARAMETER TargetDriveLetter
    The drive letter of the USB flash drive (e.g. 'D').
.PARAMETER QuickFormat
    If set, formats the target drive with the 'GhostVault' volume label as exFAT.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$TargetDriveLetter = "D",

    [Parameter(Mandatory=$false)]
    [switch]$FormatDrive
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "              GHOST-OS USB FLASH DRIVE STAGING WIZARD             " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$cleanDrive = $TargetDriveLetter.TrimEnd(":\")
$drivePath = "$($cleanDrive):\"

if (-not (Test-Path $drivePath)) {
    Write-Host "Error: Drive $drivePath not found. Please connect your USB pendrive and try again." -ForegroundColor Red
    exit 1
}

$vol = Get-Volume -DriveLetter $cleanDrive -ErrorAction SilentlyContinue
if (-not $vol) {
    Write-Host "Error: Could not retrieve volume details for $drivePath." -ForegroundColor Red
    exit 1
}

Write-Host "Detected Target USB Drive:" -ForegroundColor Yellow
Write-Host "  Drive Letter : $drivePath"
Write-Host "  Current Label: $($vol.FileSystemLabel)"
Write-Host "  File System  : $($vol.FileSystem)"
Write-Host "  Total Size   : $([math]::Round($vol.Size / 1GB, 2)) GB"
Write-Host ""

if ($FormatDrive) {
    Write-Host "WARNING: You selected -FormatDrive! All data on $drivePath will be erased." -ForegroundColor Red
    $confirm = Read-Host "Type 'YES' to format $drivePath as exFAT 'GhostVault'"
    if ($confirm -ne "YES") {
        Write-Host "Operation cancelled by user." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "[1/3] Formatting $drivePath as exFAT with label 'GhostVault'..." -ForegroundColor White
    Format-Volume -DriveLetter $cleanDrive -FileSystem exFAT -NewFileSystemLabel "GhostVault" -Force | Out-Null
    Write-Host "  ✓ Drive formatted successfully." -ForegroundColor Green
} else {
    Write-Host "[1/3] Using existing volume $drivePath (Skipping format)..." -ForegroundColor White
}

# Resolve root workspace paths
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$workspaceRoot = $repoRoot
$companionBin = Join-Path $repoRoot "windows-companion\bin\Release\net8.0-windows\win-x64\publish\Ghost-Companion.exe"
$launcherCmd = Join-Path $repoRoot "Launch-GhostOS.cmd"
$autorunInf = Join-Path $repoRoot "autorun.inf"
$docFile = Join-Path $repoRoot "docs\Ghost-OS_Official_System_Documentation.docx"
$userManual = Join-Path $repoRoot "docs\USER_MANUAL.md"

if (-not (Test-Path $companionBin)) {
    Write-Host "Error: Ghost-Companion.exe not found at $companionBin" -ForegroundColor Red
    Write-Host "Please build the project first." -ForegroundColor Red
    exit 1
}

Write-Host "[2/3] Creating standard Ghost-OS directory structure on $drivePath..." -ForegroundColor White
$dirsToCreate = @(
    "GhostVault",
    "GhostVault\backups",
    "models",
    "reports",
    "tools\win64",
    "tools\linux64",
    "docs"
)

foreach ($dir in $dirsToCreate) {
    $targetDir = Join-Path $drivePath $dir
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
}
Write-Host "  ✓ Directory structure created." -ForegroundColor Green

Write-Host "[3/3] Copying Ghost-OS portable binaries and assets..." -ForegroundColor White

Write-Host "  -> Deploying Ghost-Companion.exe (79.8 MB)..."
Copy-Item -Path $companionBin -Destination (Join-Path $drivePath "Ghost-Companion.exe") -Force

Write-Host "  -> Deploying Launch-GhostOS.cmd..."
Copy-Item -Path $launcherCmd -Destination (Join-Path $drivePath "Launch-GhostOS.cmd") -Force

Write-Host "  -> Deploying Launch-GhostOS-Remote.cmd..."
Copy-Item -Path (Join-Path $workspaceRoot "Launch-GhostOS-Remote.cmd") -Destination (Join-Path $drivePath "Launch-GhostOS-Remote.cmd") -Force

Write-Host "  -> Deploying Launch-GhostOS.command (macOS)..."
Copy-Item -Path (Join-Path $workspaceRoot "Launch-GhostOS.command") -Destination (Join-Path $drivePath "Launch-GhostOS.command") -Force

Write-Host "  -> Deploying Launch-GhostOS.sh (Linux)..."
Copy-Item -Path (Join-Path $workspaceRoot "Launch-GhostOS.sh") -Destination (Join-Path $drivePath "Launch-GhostOS.sh") -Force

Write-Host "  -> Deploying macos-companion and linux-os modules..."
$macTarget = Join-Path $drivePath "macos-companion"
if (-not (Test-Path $macTarget)) { New-Item -ItemType Directory -Path $macTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "macos-companion\*") -Destination $macTarget -Force

$linuxTarget = Join-Path $drivePath "linux-os"
if (-not (Test-Path $linuxTarget)) { New-Item -ItemType Directory -Path $linuxTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "linux-os\*") -Destination $linuxTarget -Force

Write-Host "  -> Deploying Hardware Auto-Inject & Instant Launch Suite..."
$injectTarget = Join-Path $drivePath "tools\auto-inject"
if (-not (Test-Path $injectTarget)) { New-Item -ItemType Directory -Path $injectTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "tools\auto-inject\*") -Destination $injectTarget -Force

Write-Host "  -> Deploying autorun.inf..."
Copy-Item -Path $autorunInf -Destination (Join-Path $drivePath "autorun.inf") -Force

if (Test-Path $docFile) {
    Write-Host "  -> Deploying Official Word Documentation..."
    Copy-Item -Path $docFile -Destination (Join-Path $drivePath "docs\Ghost-OS_Official_System_Documentation.docx") -Force
}

Write-Host "  -> Deploying Ghost-Core engine packages..."
$ghostCoreTarget = Join-Path $drivePath "ghost_core"
if (-not (Test-Path $ghostCoreTarget)) { New-Item -ItemType Directory -Path $ghostCoreTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "ghost-core\*") -Destination $ghostCoreTarget -Force

Write-Host "  -> Deploying Ghost-Vault cryptographic engine..."
$ghostVaultTarget = Join-Path $drivePath "ghost_vault"
if (-not (Test-Path $ghostVaultTarget)) { New-Item -ItemType Directory -Path $ghostVaultTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "ghost-vault\*") -Destination $ghostVaultTarget -Force

Write-Host "  -> Deploying Ghost-AI engine..."
$ghostAiTarget = Join-Path $drivePath "ghost_ai"
if (-not (Test-Path $ghostAiTarget)) { New-Item -ItemType Directory -Path $ghostAiTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "ghost-ai\*") -Destination $ghostAiTarget -Force

Write-Host "  -> Deploying Admin Command Center Frontend..."
$adminDistTarget = Join-Path $drivePath "admin-dashboard\dist"
if (-not (Test-Path $adminDistTarget)) { New-Item -ItemType Directory -Path $adminDistTarget -Force | Out-Null }
Copy-Item -Recurse -Path (Join-Path $workspaceRoot "admin-dashboard\dist\*") -Destination $adminDistTarget -Force

Write-Host "  -> Deploying User Manuals & System Documentation..."
if (Test-Path $userManual) {
    Copy-Item -Path $userManual -Destination (Join-Path $drivePath "USER_MANUAL.md") -Force
    Copy-Item -Path $userManual -Destination (Join-Path $drivePath "docs\USER_MANUAL.md") -Force
}
$docMdFiles = @("OFFICIAL_DOCUMENTATION.md", "SCHEMA_CONTRACT.md", "USB_PARTITION_SPEC.md")
foreach ($docName in $docMdFiles) {
    $srcDoc = Join-Path $workspaceRoot "docs\$docName"
    if (Test-Path $srcDoc) {
        Copy-Item -Path $srcDoc -Destination (Join-Path $drivePath "docs\$docName") -Force
    }
}

Write-Host "  -> Restoring Encrypted GhostVault & Recovery Keys..."
$vaultEncSrc = Join-Path $workspaceRoot "GhostVault\vault.enc"
$recKeySrc = Join-Path $workspaceRoot "GhostVault\recovery_key.txt"
if (Test-Path $vaultEncSrc) {
    Copy-Item -Path $vaultEncSrc -Destination (Join-Path $drivePath "GhostVault\vault.enc") -Force
    Write-Host "     ✓ Restored vault.enc (Master Password: Abhyas2108)" -ForegroundColor Green
}
if (Test-Path $recKeySrc) {
    Copy-Item -Path $recKeySrc -Destination (Join-Path $drivePath "GhostVault\recovery_key.txt") -Force
    Write-Host "     ✓ Restored recovery_key.txt" -ForegroundColor Green
}

# Ensure filesystem label is GhostVault
try {
    Set-Volume -DriveLetter $cleanDrive -NewFileSystemLabel "GhostVault" -ErrorAction SilentlyContinue
} catch {}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "         GHOST-OS USB FLASH DRIVE SUCCESSFULLY PREPARED!          " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your 128GB pendrive ($drivePath) is now ready to use on any PC:"
Write-Host "  1. Plug it into any Windows 10/11 computer."
Write-Host "  2. Double-click '$drivePath\Launch-GhostOS.cmd' (or Ghost-Companion.exe)."
Write-Host "  3. (Optional) Drop any compact GGUF model into '$drivePath\models\' for offline AI."
Write-Host ""
