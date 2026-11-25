<#
.SYNOPSIS
  Start the whole app so a phone can use it: backend, two Cloudflare quick
  tunnels (web + API), and a production build of the web app.

.DESCRIPTION
  Phones only allow passkeys on HTTPS sites, so the web app and the API are
  each exposed through a temporary https://*.trycloudflare.com address.
  The script reads those addresses from cloudflared and passes them to the
  backend (CORS + WebAuthn settings) and the web build as environment
  variables, so your .env files are never edited.

  Press Ctrl+C to stop the web server; the tunnels are stopped with it.
  The backend keeps running in Docker (stop it with `docker compose down`).

  Quick-tunnel addresses change on every run, and a passkey only works on the
  address it was created on, so students set up their passkey again each run.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start-phone-demo.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $env:TEMP 'secure-attendance-tunnels'
$webMetrics = '127.0.0.1:20241'
$apiMetrics = '127.0.0.1:20242'

function Get-Cloudflared {
    $command = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in @("${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    throw 'cloudflared is not installed. Run: winget install Cloudflare.cloudflared'
}

function Stop-OldTunnels {
    # Stops leftover quick tunnels to ports 3000/18000 (including ones started by hand),
    # so their metrics ports and addresses don't clash with the new ones.
    Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
        Where-Object { $_.CommandLine -match 'localhost:(3000|18000)' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Start-Tunnel([string]$exe, [int]$port, [string]$metrics, [string]$name) {
    $log = Join-Path $logDir "$name.log"
    Start-Process -FilePath $exe -WindowStyle Hidden -PassThru `
        -ArgumentList @('tunnel', '--no-autoupdate', '--metrics', $metrics, '--url', "http://localhost:$port") `
        -RedirectStandardError $log -RedirectStandardOutput "$log.out"
}

function Wait-TunnelHost([string]$metrics, [string]$name) {
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $hostname = (Invoke-RestMethod "http://$metrics/quicktunnel" -TimeoutSec 2).hostname
            if ($hostname) { return $hostname }
        } catch { }
        Start-Sleep -Seconds 1
    }
    throw "The $name tunnel did not start. See $(Join-Path $logDir "$name.log")"
}

function Wait-Url([string]$url, [int]$seconds) {
    for ($i = 0; $i -lt $seconds; $i++) {
        try {
            Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 5 | Out-Null
            return $true
        } catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

if (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Something is already running on port 3000 (an old npm run dev / npm start?). Stop it with Ctrl+C in its window, then run this again.'
}

$cloudflared = Get-Cloudflared
New-Item -ItemType Directory -Force $logDir | Out-Null
$tunnels = @()

try {
    Write-Host '1/4  Starting tunnels...' -ForegroundColor Cyan
    Stop-OldTunnels
    $tunnels += Start-Tunnel $cloudflared 3000 $webMetrics 'web'
    $tunnels += Start-Tunnel $cloudflared 18000 $apiMetrics 'api'
    $webHost = Wait-TunnelHost $webMetrics 'web'
    $apiHost = Wait-TunnelHost $apiMetrics 'api'
    $webUrl = "https://$webHost"
    $apiUrl = "https://$apiHost"
    Write-Host "     web: $webUrl"
    Write-Host "     api: $apiUrl"

    Write-Host '2/4  Starting backend with the tunnel addresses...' -ForegroundColor Cyan
    # Shell variables override .env for Docker Compose.
    $env:CORS_ORIGINS = "[`"http://localhost:3000`",`"$webUrl`"]"
    $env:WEBAUTHN_RP_ID = $webHost
    $env:WEBAUTHN_ORIGINS = "[`"$webUrl`"]"
    Push-Location $repoRoot
    try {
        docker compose up -d
        if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed. Is Docker Desktop running?' }
    } finally { Pop-Location }
    if (-not (Wait-Url "$apiUrl/health" 90)) {
        throw "The backend isn't answering at $apiUrl/health. Check: docker compose logs backend"
    }

    Write-Host '3/4  Building the web app...' -ForegroundColor Cyan
    # Next.js keeps an existing process variable over web\.env.local.
    $env:NEXT_PUBLIC_API_URL = $apiUrl
    Push-Location (Join-Path $repoRoot 'web')
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'npm run build failed.' }

        Write-Host ''
        Write-Host '4/4  Ready. Open this on the PC (professor) AND the phone (student):' -ForegroundColor Green
        Write-Host ''
        Write-Host "     $webUrl" -ForegroundColor Yellow
        Write-Host ''
        Write-Host '     Use this address on the PC too, not localhost. Press Ctrl+C to stop.'
        Write-Host ''
        try { Set-Clipboard -Value $webUrl; Write-Host '     (Address copied to the clipboard.)' } catch { }
        npm start
    } finally { Pop-Location }
}
finally {
    foreach ($tunnel in $tunnels) {
        Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host 'Tunnels stopped. The backend is still running (docker compose down to stop it).'
}
