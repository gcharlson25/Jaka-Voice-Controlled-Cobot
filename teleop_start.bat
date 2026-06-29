@echo off
echo Starting Teleop System...
echo.

echo [1] Starting robot client (Python 3.7)...
start "Robot Client" cmd /k python robot_client.py

timeout /t 3 /nobreak >nul

echo [2] Starting vision server (Python 3.12)...
start "Vision Server" cmd /k py -3.12 vision_server.py

echo.
echo Both processes launched. Close the windows to stop.
