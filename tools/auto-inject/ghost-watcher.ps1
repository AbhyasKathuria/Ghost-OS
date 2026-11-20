# Ghost-OS Native USB Arrival Watcher
# Silently listens for USB drive insertion and auto-launches Ghost-OS

$query = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"
Register-WmiEvent -Query $query -SourceIdentifier "GhostUSBArrival" -Action {
    $drive = $Event.SourceEventArgs.NewEvent.DriveName
    if ($drive -and (Test-Path "$drive\Launch-GhostOS.cmd")) {
        Start-Process "$drive\Launch-GhostOS.cmd"
    }
}

# Keep background process alive
while ($true) {
    Start-Sleep -Seconds 3600
}
