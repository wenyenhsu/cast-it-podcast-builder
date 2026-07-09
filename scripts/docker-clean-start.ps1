# Docker Desktop on Windows can leave undeletable "ghost" unix-socket files
# after an unclean shutdown (crash/BSOD). On the next start it fails with
# "remove ...sock: The file cannot be accessed by the system." This script
# moves those directories aside and then launches Docker Desktop.
# Used by the "Docker Desktop" autostart entry (HKCU Run key).

$ErrorActionPreference = "SilentlyContinue"

$socketDirs = @(
    "$env:LOCALAPPDATA\Docker\run",
    "$env:LOCALAPPDATA\docker-secrets-engine"
)

foreach ($dir in $socketDirs) {
    if (Test-Path $dir) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        Rename-Item $dir "$dir.stale.$stamp"
        New-Item -ItemType Directory $dir -Force | Out-Null
    }
    # Prune older stale copies (keep the disk clean)
    Get-ChildItem "$dir.stale.*" -Directory |
        Sort-Object Name -Descending |
        Select-Object -Skip 3 |
        Remove-Item -Recurse -Force
}

Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
