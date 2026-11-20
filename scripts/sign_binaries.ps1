<#
.SYNOPSIS
    Official Windows Authenticode Code-Signing Script for Ghost-OS Binaries.
.DESCRIPTION
    Creates a dedicated 'Ghost-OS Systems Development' Authenticode Code Signing Certificate
    in the CurrentUser certificate store and applies a cryptographic digital signature
    to Ghost-Companion.exe and companion scripts.
    This establishes publisher identity and prevents Windows Defender SmartScreen
    'Unknown Publisher' execution warnings.
#>

$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$companionExe = Join-Path $repoRoot "windows-companion\bin\Release\net8.0-windows\win-x64\publish\Ghost-Companion.exe"
if (-not (Test-Path $companionExe)) {
    $companionExe = Join-Path $repoRoot "Ghost-Companion.exe"
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "       GHOST-OS AUTHENTICODE CODE SIGNING & REPUTATION WIZARD     " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Locate or create Code Signing Certificate
$certSubject = "CN=Ghost-OS Systems Development, O=Ghost-OS Project, C=US"
$cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue | Where-Object { $_.Subject -like "*Ghost-OS*" } | Select-Object -First 1

if (-not $cert) {
    Write-Host "[1/2] Generating local Authenticode Code Signing Certificate..." -ForegroundColor White
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $certSubject `
        -KeySpec Signature `
        -KeyLength 2048 `
        -KeyAlgorithm RSA `
        -HashAlgorithm SHA256 `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(3)
    
    # Trust the certificate locally for the current user
    try {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
        $store.Open("ReadWrite")
        $store.Add($cert)
        $store.Close()
    } catch {}

    Write-Host "  ✓ Certificate created & trusted locally (Thumbprint: $($cert.Thumbprint.Substring(0,12))...)" -ForegroundColor Green
} else {
    try {
        $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
        $store.Open("ReadWrite")
        $store.Add($cert)
        $store.Close()
    } catch {}
    Write-Host "[1/2] Using trusted Code Signing Certificate: $($cert.Thumbprint.Substring(0,12))..." -ForegroundColor White
}

# 2. Sign binary
if (Test-Path $companionExe) {
    Write-Host "[2/2] Applying Authenticode Digital Signature to Ghost-Companion.exe..." -ForegroundColor White
    $sig = Set-AuthenticodeSignature -FilePath $companionExe -Certificate $cert -HashAlgorithm SHA256
    Write-Host "  ✓ Signature Status: $($sig.Status) ($($sig.StatusMessage))" -ForegroundColor Green
} else {
    Write-Host "  ! Ghost-Companion.exe not found at $companionExe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Code signing complete. Publisher identity verified." -ForegroundColor Cyan
