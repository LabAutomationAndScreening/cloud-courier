@echo off
setlocal enabledelayedexpansion

REM Check if the artifact zip exists
if not exist cloud-courier-deployment-package.zip (
    echo cloud-courier-deployment-package.zip not found. Please ensure the artifact is in the current directory.
    pause
    exit /b 1
)

echo Extracting cloud-courier-deployment-package.zip...
tar -xf cloud-courier-deployment-package.zip

REM Load the backend Docker image
echo Loading backend Docker image...
docker load -i cloud-courier-backend.tar
if %errorlevel% neq 0 (
    echo Failed to load backend Docker image.
    pause
    exit /b 1
)

REM Load the frontend Docker image
echo Loading frontend Docker image...
docker load -i cloud-courier-frontend.tar
if %errorlevel% neq 0 (
    echo Failed to load frontend Docker image.
    pause
    exit /b 1
)

echo Docker images have been loaded successfully.

REM Ask user if they want to restart the stack
set /p RESTART_STACK="Do you want to restart the stack? (Y/N): "

if /I "%RESTART_STACK%"=="Y" (
    REM Set project name explicitly
    set PROJECT_NAME=cloud-courier

    echo Stopping existing stack...
    REM Remove everything in the existing stack so we have a clean slate
    docker-compose --project-name !PROJECT_NAME! down --remove-orphans --volumes

    echo Starting stack...
    docker-compose --project-name !PROJECT_NAME! up -d

    echo Stack restarted successfully.
) else (
    echo Skipping stack restart.
)

pause
exit /b 0

REM ============== WARNING ==============================================================================
REM File is managed by copier template: gh:LabAutomationAndScreening/copier-nuxt-python-intranet-app.git
REM See .config/.copier-managed-files.json for details.
REM
REM You are welcome to make changes to this file in your repo if they are custom to your project,
REM but if the change should be shared with other projects, please backport it to the template repo.
REM =====================================================================================================
