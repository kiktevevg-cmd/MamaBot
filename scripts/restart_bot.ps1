# Kill duplicate MamaBot python processes, then start a single instance.
$ErrorActionPreference = "SilentlyContinue"
$root = "C:\Users\Kikte\Documents\Cursor progect\Mom"
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | ForEach-Object {
    if ($_.CommandLine -and ($_.CommandLine -like "*Mom*bot.py*" -or $_.CommandLine -like "*Mom*\\bot.py*")) {
        Write-Host "Stopping PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force
    }
}
Start-Sleep -Seconds 2
Set-Location $root
& "$root\venv\Scripts\python.exe" -u bot.py
