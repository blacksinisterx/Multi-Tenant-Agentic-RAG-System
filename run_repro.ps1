# Reproducible run script for Assignment 2
# Place this in the repository root and run from PowerShell.
# Usage: Open PowerShell, cd to the repo root, then: .\run_repro.ps1

$PY = "D:\FAST\Semester 7\Agentic AI\Assignments\Assignment 2\.venv\Scripts\python.exe"
$Config = "config.yaml"

# Ensure we run from the script's directory (repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

function Wait-ForOllama {
    param(
        [int]$TimeoutSeconds = 30
    )
    Write-Host "Waiting for Ollama on localhost:11434 (timeout ${TimeoutSeconds}s)..."
    for ($i=0; $i -lt $TimeoutSeconds; $i++) {
        try {
            $res = Test-NetConnection -ComputerName 'localhost' -Port 11434 -WarningAction SilentlyContinue
            if ($res.TcpTestSucceeded) {
                Write-Host "Ollama is reachable."
                return $true
            }
        } catch {
            # ignore
        }
        Start-Sleep -Seconds 1
    }
    Write-Warning "Ollama did not respond on port 11434 within timeout. The script will continue but runs may be non-deterministic."
    return $false
}

# Start
Write-Host "Starting reproducible run sequence..."
Wait-ForOllama -TimeoutSeconds 20

Write-Host "1) Rebuilding indices (this may take a minute)..."
& "$PY" -c "from retrieval.index import Retriever; r=Retriever('.'); r.build_or_update(); print('Built indices')"
if ($LASTEXITCODE -ne 0) { Write-Warning "Index build returned non-zero exit code: $LASTEXITCODE" }

Write-Host "2) Running red-team runner (writes eval/redteam_results.json)..."
& "$PY" -m tools.run_redteam --config $Config
if ($LASTEXITCODE -ne 0) { Write-Warning "tools.run_redteam returned non-zero exit code: $LASTEXITCODE" }

Write-Host "3) Running evaluation harness (writes eval/results.json)..."
& "$PY" -m eval.run_eval --config $Config
if ($LASTEXITCODE -ne 0) { Write-Warning "eval.run_eval returned non-zero exit code: $LASTEXITCODE" }

Write-Host "4) Running tests (pytest -q)..."
& "$PY" -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Warning "pytest returned non-zero exit code: $LASTEXITCODE" }

Write-Host "Run sequence complete. Check eval/results.json, eval/redteam_results.json and logs/run.jsonl for outputs."
Get-ChildItem -Path .\eval\ -Filter *.json

# Show summary of results.json (first 300 chars)
if (Test-Path .\eval\results.json) {
    Write-Host "\n--- eval/results.json (preview) ---"
    Get-Content .\eval\results.json -Raw | Select-Object -First 1 | ForEach-Object { $_.Substring(0, [Math]::Min(300,$_.Length)) }
}

Write-Host "Done."