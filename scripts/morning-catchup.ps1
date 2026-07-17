# If no episode was created today by mid-morning, run the daily pipeline.
# Scheduled as "MorningCatchup": daily 09:45, repeating every 2 hours until
# evening. Covers mornings the Beat scheduler missed (crash, BitLocker
# prompt, Docker outage) once the machine is back.

$log = "$PSScriptRoot\..\logs\morning-catchup.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log($msg) { "$(Get-Date -Format s) $msg" | Add-Content $log }

trap {
    Log "FATAL: $_"
    exit 1
}

Log "catch-up cycle started"

# Just after login, PATH and services may not be ready yet — settle first.
Start-Sleep -Seconds 60

# Make sure the host services are alive first (also starts Docker).
& "$PSScriptRoot\pipeline-watchdog.ps1"

# Wait for the API (up to 5 minutes — Docker may just be starting).
$deadline = (Get-Date).AddMinutes(5)
$apiUp = $false
while ((Get-Date) -lt $deadline) {
    try {
        Invoke-RestMethod "http://localhost:8000/api/v1/health/live/" -TimeoutSec 5 | Out-Null
        $apiUp = $true; break
    } catch { Start-Sleep 10 }
}
if (-not $apiUp) { Log "API not reachable; giving up this cycle"; exit 1 }

# Already have an episode today? Then nothing to do.
try {
    $r = Invoke-RestMethod "http://localhost:8000/api/v1/episodes/?ordering=-created_at&page_size=1" -TimeoutSec 15
    $latest = $r.results[0].created_at
    if ($latest -and ([datetime]$latest).Date -eq (Get-Date).Date) {
        Log "episode already exists today ($latest); ok"
        exit 0
    }
} catch { Log "episode check failed: $_"; exit 1 }

Log "no episode today - running catch-up pipeline"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }
& $py "$PSScriptRoot\run_daily.py" *>> $log
Log "catch-up finished with exit code $LASTEXITCODE"
