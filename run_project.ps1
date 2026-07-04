param(
    [string]$PmidsFile,
    [string]$OutDir,
    [ValidateSet("append", "overwrite")]
    [string]$Mode,
    [int]$Cores = 1,
    [string]$CondaExe
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Write-Title {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Phospholipid Protein LLM Mining Runner" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Resolve-PathOrCreate {
    param([string]$PathValue, [bool]$MustExist)
    if ($MustExist) {
        return (Resolve-Path -LiteralPath $PathValue).Path
    }
    New-Item -ItemType Directory -Force -Path $PathValue | Out-Null
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Read-RequiredPath {
    param([string]$Prompt, [bool]$MustExist)
    while ($true) {
        $value = Read-Host $Prompt
        $value = $value.Trim('"').Trim()
        if ([string]::IsNullOrWhiteSpace($value)) {
            Write-Host "Path cannot be empty." -ForegroundColor Yellow
            continue
        }
        if ($MustExist -and -not (Test-Path -LiteralPath $value)) {
            Write-Host "File not found: $value" -ForegroundColor Yellow
            continue
        }
        return (Resolve-PathOrCreate $value $MustExist)
    }
}

function Read-RunMode {
    while ($true) {
        Write-Host ""
        Write-Host "[3/4] Select run mode:"
        Write-Host "1. append    keep cache and process new PMIDs"
        Write-Host "2. overwrite clear old cache/results and rerun all PMIDs"
        $choice = Read-Host "Enter 1 or 2"
        switch ($choice.Trim()) {
            "1" { return "append" }
            "2" { return "overwrite" }
            default { Write-Host "Please enter 1 or 2." -ForegroundColor Yellow }
        }
    }
}

function Find-Conda {
    param([string]$Provided)
    if ($Provided -and (Test-Path -LiteralPath $Provided)) {
        return (Resolve-Path -LiteralPath $Provided).Path
    }
    $cmd = Get-Command conda -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        "$env:USERPROFILE\miniforge3\Scripts\conda.exe",
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\miniforge3\Scripts\conda.exe",
        "$env:LOCALAPPDATA\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\miniforge3\Scripts\conda.exe",
        "C:\ProgramData\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\anaconda3\Scripts\conda.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Install-Miniforge {
    $target = Join-Path $env:USERPROFILE "miniforge3"
    $condaPath = Join-Path $target "Scripts\conda.exe"
    if (Test-Path -LiteralPath $condaPath) {
        return $condaPath
    }

    Write-Host "Conda was not found. Miniforge will be installed to: $target" -ForegroundColor Yellow
    $agree = Read-Host "Download and install Miniforge now? Enter Y to continue"
    if ($agree -notmatch "^[Yy]$") {
        throw "Miniforge installation cancelled."
    }

    $installer = Join-Path $env:TEMP "Miniforge3-Windows-x86_64.exe"
    $url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
    Write-Host "Downloading Miniforge..."
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Write-Host "Installing Miniforge..."
    Start-Process -FilePath $installer -ArgumentList @("/S", "/InstallationType=JustMe", "/AddToPath=0", "/RegisterPython=0", "/D=$target") -Wait -WindowStyle Hidden
    if (-not (Test-Path -LiteralPath $condaPath)) {
        throw "Miniforge installed, but conda.exe was not found: $condaPath"
    }
    return $condaPath
}

function Ensure-CondaEnv {
    param([string]$CondaPath)
    $envName = "phospholipid-llm-mining"
    $envList = & $CondaPath env list
    if ($envList -match "^\s*$envName\s+") {
        Write-Host "Conda environment exists: $envName" -ForegroundColor Green
        return
    }

    Write-Host "Conda environment not found: $envName" -ForegroundColor Yellow
    Write-Host "Creating environment from environment.yml..."
    & $CondaPath env create -f (Join-Path $ProjectRoot "environment.yml")
}

function Ensure-LlmEnv {
    $envFile = Join-Path $ProjectRoot ".env"
    $existing = @{}
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match "^\s*([^#=]+)=(.*)$") {
                $existing[$matches[1].Trim()] = $matches[2].Trim()
            }
        }
    }

    $apiKey = $existing["LLM_API_KEY"]
    $baseUrl = $existing["LLM_BASE_URL"]
    $model = $existing["LLM_MODEL"]

    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Host "LLM_API_KEY was not found." -ForegroundColor Yellow
        $apiKey = Read-Host "Enter LLM API key"
    }
    if ([string]::IsNullOrWhiteSpace($baseUrl)) {
        $baseUrl = Read-Host "Enter LLM_BASE_URL (press Enter for https://api.deepseek.com)"
        if ([string]::IsNullOrWhiteSpace($baseUrl)) {
            $baseUrl = "https://api.deepseek.com"
        }
    }
    if ([string]::IsNullOrWhiteSpace($model)) {
        $model = Read-Host "Enter LLM_MODEL (press Enter for deepseek-v4-flash)"
        if ([string]::IsNullOrWhiteSpace($model)) {
            $model = "deepseek-v4-flash"
        }
    }

    $content = @(
        "LLM_API_KEY=$apiKey",
        "LLM_BASE_URL=$baseUrl",
        "LLM_MODEL=$model"
    ) -join "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($envFile, $content + "`n", $utf8NoBom)
    Write-Host "LLM config saved to local .env. It is ignored by Git." -ForegroundColor Green
}

function Copy-Pmids {
    param([string]$Source, [string]$Destination)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Write-RunConfig {
    param([string]$OutputRoot)
    $runDir = Join-Path $OutputRoot ".run"
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
    $configPath = Join-Path $runDir "config.yaml"
    $pmidsPath = (Join-Path $OutputRoot "input\pmids.txt").Replace("\", "/")
    $articlesPath = (Join-Path $OutputRoot "cache\articles_pubmed.csv").Replace("\", "/")
    $preparedPath = (Join-Path $OutputRoot "cache\prepared_articles.jsonl").Replace("\", "/")
    $rawDirPath = (Join-Path $OutputRoot "cache\raw_llm_outputs").Replace("\", "/")
    $llmRawPath = (Join-Path $OutputRoot "cache\llm_extracted_raw.jsonl").Replace("\", "/")
    $recordsPath = (Join-Path $OutputRoot "results\extracted_records.csv").Replace("\", "/")
    $failedPath = (Join-Path $OutputRoot "results\failed_records.csv").Replace("\", "/")
    $sqlitePath = (Join-Path $OutputRoot "results\phospholipid_protein.sqlite").Replace("\", "/")
    $summaryPath = (Join-Path $OutputRoot "results\extraction_summary.json").Replace("\", "/")
    $yaml = @"
project:
  name: phospholipid_llm_mining
  prompt_version: v0.1.0

paths:
  pmids: "$pmidsPath"
  articles_csv: "$articlesPath"
  prepared_articles: "$preparedPath"
  raw_llm_dir: "$rawDirPath"
  llm_raw_jsonl: "$llmRawPath"
  normalized_csv: "$recordsPath"
  failed_csv: "$failedPath"
  sqlite_db: "$sqlitePath"
  summary_json: "$summaryPath"

pubmed:
  email: ""
  tool: phospholipid-llm-mining
  batch_size: 20
  timeout_seconds: 30

llm:
  mode: api
  provider: openai_compatible
  base_url: "`${LLM_BASE_URL:-https://api.deepseek.com}"
  api_key_env: LLM_API_KEY
  model: "`${LLM_MODEL:-deepseek-v4-flash}"
  temperature: 0
  max_retries: 2
  timeout_seconds: 60
  mock_dir: examples/mock_llm_outputs
"@
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($configPath, $yaml, $utf8NoBom)
    return $configPath
}

function Prepare-OutputDirectory {
    param([string]$OutputRoot, [string]$RunMode)
    New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
    if ($RunMode -eq "overwrite") {
        foreach ($child in @("cache", "results", "logs", ".run")) {
            $path = Join-Path $OutputRoot $child
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Recurse -Force
            }
        }
    }
    foreach ($child in @("input", "cache", "results", "logs", ".run")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $OutputRoot $child) | Out-Null
    }
}

function Run-Workflow {
    param([string]$CondaPath, [string]$ConfigPath, [string]$OutputRoot)
    $logPath = Join-Path $OutputRoot "logs\snakemake.log"
    Write-Host "Running Snakemake workflow..."
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $command = "`"`"$CondaPath`" run -n phospholipid-llm-mining snakemake --cores $Cores --configfile `"$ConfigPath`" 2>&1`""
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c $command"
    $psi.WorkingDirectory = $ProjectRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $process.WaitForExit()
    $combined = $stdout.Trim()
    if ($combined) {
        $combined | Tee-Object -FilePath $logPath
    } else {
        Set-Content -Path $logPath -Value "" -Encoding UTF8
    }
    $exitCode = $process.ExitCode
    if ($exitCode -ne 0) {
        throw "Snakemake failed. Log: $logPath"
    }
}

Write-Title

if (-not $PmidsFile) {
    $PmidsFile = Read-RequiredPath "[1/4] Enter PMID list file path" $true
}
if (-not $OutDir) {
    $OutDir = Read-RequiredPath "[2/4] Enter output directory path" $false
} else {
    $OutDir = Resolve-PathOrCreate $OutDir $false
}
if (-not $Mode) {
    $Mode = Read-RunMode
}

$CondaExe = Find-Conda $CondaExe
if (-not $CondaExe) {
    $CondaExe = Install-Miniforge
}

Write-Host ""
Write-Host "[4/4] Configuration check:" -ForegroundColor Cyan
Write-Host "PMID file: $PmidsFile"
Write-Host "Output dir: $OutDir"
Write-Host "Mode: $Mode"
Write-Host "Conda: $CondaExe"

Ensure-CondaEnv $CondaExe
Ensure-LlmEnv

if ($MyInvocation.BoundParameters.Count -eq 0) {
    $confirm = Read-Host "Start running now? Enter Y to continue"
    if ($confirm -notmatch "^[Yy]$") {
        throw "Run cancelled."
    }
}

Prepare-OutputDirectory $OutDir $Mode
Copy-Pmids $PmidsFile (Join-Path $OutDir "input\pmids.txt")
$configPath = Write-RunConfig $OutDir
Run-Workflow $CondaExe $configPath $OutDir

Write-Host ""
Write-Host "Run complete." -ForegroundColor Green
Write-Host "Main CSV: $(Join-Path $OutDir 'results\extracted_records.csv')"
Write-Host "SQLite DB: $(Join-Path $OutDir 'results\phospholipid_protein.sqlite')"
Write-Host "Summary: $(Join-Path $OutDir 'results\extraction_summary.json')"
Write-Host "Log: $(Join-Path $OutDir 'logs\snakemake.log')"
