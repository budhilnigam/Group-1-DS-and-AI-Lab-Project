@echo off
cd /d "%~dp0"

pip install -r requirements.txt
REM If you want to enable automatic package installation, uncomment
REM the line above or add a safe check to install only missing packages.

docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running or not available in PATH.
    echo Checking whether Docker is installed...
    where docker >nul 2>&1
    if errorlevel 1 (
        echo Docker is not installed. Please install Docker and start it, then try again.
        exit /b 1
    )
    echo Docker is installed but not running. Attempting to start Docker...
    sc query com.docker.service >nul 2>&1
    if errorlevel 1 (
        echo Docker service not found; attempting to launch Docker Desktop.
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" >nul 2>&1
    ) else (
        echo Starting Docker service...
        net start com.docker.service >nul 2>&1
        if errorlevel 1 (
            echo Failed to start Docker service; attempting to launch Docker Desktop instead.
            start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" >nul 2>&1
        )
    )
    goto docker_wait
)

:docker_wait
echo Waiting for Docker to become available...
set /a tries=0
:docker_wait_loop
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
if %tries% geq 30 (
    echo Docker did not start within timeout. Please start Docker manually and retry.
    exit /b 1
)
set /a tries+=1
timeout /t 1 /nobreak >nul
goto docker_wait_loop

:docker_ok
echo Docker is running.

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

docker run -d --rm --name qdrant_review -p 6333:6333 -p 6334:6334 -v qdrant-storage:/qdrant/storage qdrant/qdrant:latest

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
echo Starting web server on port 8080...
echo Open http://127.0.0.1:8080 in your browser.
echo Press Ctrl+C to stop.
python -m uvicorn app:app --host 0.0.0.0 --port 8080
