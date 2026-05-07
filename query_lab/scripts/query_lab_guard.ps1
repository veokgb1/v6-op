param(
    [ValidateSet("status", "start", "stop", "tail")]
    [string]$Action = "status",

    [ValidateSet("astock", "sector", "all")]
    [string]$Route = "astock",

    [string]$Group = "A1_basic",
    [int]$Limit = 5,
    [int]$Repeat = 1,
    [int]$SleepMs = 3000,
    [int]$TailLines = 80,
    [int]$FetchLimit = 300,
    [int]$QueryTimeoutSec = 60
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ResultsDir = Join-Path $Root "query_lab\results"
$LogsDir = Join-Path $ResultsDir "logs"
$CurrentFile = Join-Path $ResultsDir "query_lab_current.json"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

function Get-QueryLabProcess {
    Get-CimInstance Win32_Process -Filter "name='python.exe'" |
        Where-Object { $_.CommandLine -like "*query_lab*run_query_lab.py*" }
}

function Show-RecentRuns {
    $runsDir = Join-Path $ResultsDir "runs"
    if (-not (Test-Path $runsDir)) { return }
    Get-ChildItem -Path $runsDir -Directory |
        Sort-Object Name -Descending |
        Select-Object -First 8 |
        ForEach-Object {
            $files = Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue
            [PSCustomObject]@{
                Run = $_.Name
                Files = $files.Count
                LastWrite = $_.LastWriteTime
            }
        } |
        Format-Table -AutoSize
}

Set-Location $Root

if ($Action -eq "status") {
    Write-Host "[QueryLabGuard] processes"
    $procs = Get-QueryLabProcess
    if ($procs) {
        $procs | Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine | Format-List
    } else {
        Write-Host "No query_lab run process."
    }

    if (Test-Path $CurrentFile) {
        Write-Host ""
        Write-Host "[QueryLabGuard] current"
        Get-Content -Encoding UTF8 -Path $CurrentFile
    }

    Write-Host ""
    Write-Host "[QueryLabGuard] recent runs"
    Show-RecentRuns
    exit 0
}

if ($Action -eq "stop") {
    $procs = Get-QueryLabProcess
    if (-not $procs) {
        Write-Host "[QueryLabGuard] No query_lab run process to stop."
        exit 0
    }
    $procs | Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine | Format-List
    $procs | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[QueryLabGuard] stopped query_lab run process(es)."
    exit 0
}

if ($Action -eq "tail") {
    if (-not (Test-Path $CurrentFile)) {
        Write-Host "[QueryLabGuard] no current file."
        exit 1
    }
    $current = Get-Content -Encoding UTF8 -Raw -Path $CurrentFile | ConvertFrom-Json
    if (-not (Test-Path $current.stdout_log)) {
        Write-Host "[QueryLabGuard] stdout log not found: $($current.stdout_log)"
        exit 1
    }
    Get-Content -Encoding UTF8 -Path $current.stdout_log -Tail $TailLines
    exit 0
}

if ($Action -eq "start") {
    $running = Get-QueryLabProcess
    if ($running) {
        Write-Host "[QueryLabGuard] Refuse to start: query_lab process already running."
        $running | Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine | Format-List
        exit 2
    }

    $env:NODE_NO_WARNINGS = "1"
    $env:PYTHONUNBUFFERED = "1"
    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdoutLog = Join-Path $LogsDir "query_lab_${Route}_${Group}_${ts}.log"
    $stderrLog = Join-Path $LogsDir "query_lab_${Route}_${Group}_${ts}.err.log"

    $argList = @(".\query_lab\scripts\run_query_lab.py", "--route", $Route, "--repeat", "$Repeat", "--sleep-ms", "$SleepMs")
    if ($Group) {
        $argList += @("--group", $Group)
    }
    if ($Limit -gt 0) {
        $argList += @("--limit", "$Limit")
    }
    $argList += @("--fetch-limit", "$FetchLimit")
    $argList += @("--query-timeout-sec", "$QueryTimeoutSec")

    $proc = Start-Process `
        -FilePath ".\.venv\Scripts\python.exe" `
        -ArgumentList (@("-u") + $argList) `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog

    $state = [PSCustomObject]@{
        pid = $proc.Id
        started_at = (Get-Date).ToString("s")
        route = $Route
        group = $Group
        limit = $Limit
        repeat = $Repeat
        sleep_ms = $SleepMs
        fetch_limit = $FetchLimit
        query_timeout_sec = $QueryTimeoutSec
        stdout_log = $stdoutLog
        stderr_log = $stderrLog
        command = ".\.venv\Scripts\python.exe " + ($argList -join " ")
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $CurrentFile

    Write-Host "[QueryLabGuard] started pid=$($proc.Id)"
    Write-Host "[QueryLabGuard] stdout=$stdoutLog"
    Write-Host "[QueryLabGuard] stderr=$stderrLog"
    Write-Host "[QueryLabGuard] status: powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status"
    Write-Host "[QueryLabGuard] tail:   powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action tail"
    Write-Host "[QueryLabGuard] stop:   powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop"
    exit 0
}
