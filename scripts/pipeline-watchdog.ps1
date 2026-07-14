# Keeps the Cast It pipeline's host services alive. Runs every 30 minutes
# via the "PipelineWatchdog" scheduled task. Restarts whatever is down:
#   - Docker Desktop (via clean-start, which clears ghost socket files)
#   - Ollama (LLM server on :11434)
#   - Chatterbox TTS (via its scheduled task, serves :8004)

function Test-Http($url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Docker engine
docker ps 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    & "$PSScriptRoot\docker-clean-start.ps1"
}

# Ollama
if (-not (Test-Http "http://localhost:11434/api/tags")) {
    Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe" -ArgumentList "--hide"
}

# Chatterbox TTS
if (-not (Test-Http "http://localhost:8004/api/ui/initial-data")) {
    Start-ScheduledTask -TaskName "ChatterboxTTS" -ErrorAction SilentlyContinue
}
