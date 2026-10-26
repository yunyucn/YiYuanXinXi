@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = 5000,5173; $pids = @(Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); foreach ($processId in $pids) { Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue }; if ($pids.Count -eq 0) { Write-Host 'No services are running on ports 5000/5173.' } else { Write-Host 'Stopped services on ports 5000/5173.' }"
pause
endlocal