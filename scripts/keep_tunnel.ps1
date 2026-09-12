# Keeps an HTTPS tunnel to local API:8000 and refreshes Telegram Mini App URL.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Update-EnvUrl([string]$Url) {
    $envPath = Join-Path $Root ".env"
    $content = Get-Content $envPath -Raw
    $content = $content -replace 'WEBAPP_URL=.*', "WEBAPP_URL=$Url"
    $content = $content -replace 'API_URL=.*', "API_URL=$Url"
    Set-Content -Path $envPath -Value $content -NoNewline
}

function Update-TelegramMenu([string]$Url) {
    $py = Join-Path $Root "venv\Scripts\python.exe"
    $code = @"
import asyncio
from aiogram import Bot
from aiogram.types import MenuButtonCommands
from dotenv import load_dotenv
import os
load_dotenv()
token = os.getenv('BOT_TOKEN')
async def main():
    bot = Bot(token=token)
    # Keep menu collapsed (commands); do not expand Mini App button
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    print('menu ok collapsed', os.getenv('WEBAPP_URL'))
    await bot.session.close()
asyncio.run(main())
"@
    $env:PYTHONPATH = $Root
    & $py -c $code
}

Write-Host "Starting tunnel watchdog (localhost.run)..."
while ($true) {
    $log = Join-Path $Root "logs\tunnel_watch.log"
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "ssh"
    $psi.Arguments = "-o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()

    $found = $false
    while (-not $proc.HasExited) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -eq $line) {
            Start-Sleep -Milliseconds 200
            if ($proc.HasExited) { break }
            continue
        }
        Add-Content -Path $log -Value $line
        Write-Host $line
        if ($line -match 'https://[a-zA-Z0-9.-]+\.lhr\.life') {
            $url = $Matches[0]
            if (-not $found) {
                $found = $true
                Write-Host "Tunnel URL: $url"
                Update-EnvUrl $url
                try { Update-TelegramMenu $url } catch { Write-Host $_ }
            }
        }
    }
    Write-Host "Tunnel disconnected, restarting in 3s..."
    Start-Sleep -Seconds 3
}
