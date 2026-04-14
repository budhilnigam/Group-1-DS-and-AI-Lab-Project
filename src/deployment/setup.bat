@echo off
cd /d "%~dp0"

pip install -r requirements.txt

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please install and start Docker, then try again.
    exit /b 1
)

curl -s http://localhost:6333/healthz >nul 2>&1
if not errorlevel 1 (
    echo Qdrant already running on port 6333.
    goto qdrant_ready
)

set QDRANT_CONTAINER=qdrant_review

docker ps -a --format "{{.Names}}" | findstr /x "%QDRANT_CONTAINER%" >nul 2>&1
if not errorlevel 1 (
    docker start %QDRANT_CONTAINER%
    goto qdrant_wait
)

docker run -d --name %QDRANT_CONTAINER% -p 6333:6333 qdrant/qdrant:latest

:qdrant_wait
echo Waiting for Qdrant...
set /a tries=0
:wait_loop
if %tries% geq 30 goto qdrant_ready
curl -s http://localhost:6333/healthz >nul 2>&1
if not errorlevel 1 goto qdrant_ready
set /a tries+=1
timeout /t 1 /nobreak >nul
goto wait_loop

:qdrant_ready

tasklist /fi "imagename eq celery.exe" 2>nul | find /i "celery" >nul
if not errorlevel 1 (
    echo Celery worker already running.
) else (
    start /b celery -A worker worker --beat --loglevel=info --concurrency=1
    timeout /t 3 /nobreak >nul
)

echo Starting web server on port 8080...
echo Open http://127.0.0.1:8080 in your browser.
echo Press Ctrl+C to stop.
python -m uvicorn app:app --host 0.0.0.0 --port 8080
