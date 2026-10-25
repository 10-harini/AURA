@echo off
echo ============================================
echo   Nexus Desktop Assistant - Setup
echo ============================================
echo.

echo [1/3] Installing Python dependencies...
pip install flask flask-cors pycaw comtypes psutil
echo.

echo [2/3] Installing Node dependencies (Electron)...
npm install
echo.

echo [3/3] Done! Starting app...
npm start
