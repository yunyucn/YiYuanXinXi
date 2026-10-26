@echo off
setlocal
cd /d "%~dp0"
start "BloodBank Backend" cmd /k "cd /d ""%~dp0backend"" && python app.py"
start "BloodBank Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
endlocal