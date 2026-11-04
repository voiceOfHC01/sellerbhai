@echo off
title SellerBhai Launcher
echo ===================================================
echo           Starting SellerBhai Local Server
echo ===================================================

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "SellerBhai Backend" cmd /c "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting Vite React Frontend on http://localhost:5173 ...
start "SellerBhai Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo Waiting for servers to initialize...
timeout /t 3 >nul
start http://localhost:5173

echo.
echo Login Credentials:
echo Email:    admin@replybd.com
echo Password: admin_secure_pass_2026
echo.
pause
