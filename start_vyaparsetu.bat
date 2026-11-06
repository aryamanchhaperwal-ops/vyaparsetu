@echo off
echo =====================================================================
echo                VyaparSetu - AI MSME Financial Platform
echo =====================================================================
echo.
echo Starting FastAPI Backend on port 8000 and Next.js Frontend on port 3000...
echo.

start "VyaparSetu Backend API (FastAPI)" cmd /k "cd /d %~dp0 && .\.venv\Scripts\activate.bat && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak > nul

start "VyaparSetu Frontend (Next.js)" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo =====================================================================
echo Services started!
echo Frontend: http://localhost:3000
echo Backend API Docs: http://127.0.0.1:8000/docs
echo Demo Credentials: demo@vyaparsetu.in / VyaparSetu@2026
echo =====================================================================
