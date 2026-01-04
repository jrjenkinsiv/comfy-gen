@echo off
REM Start ComfyUI server in API mode on moira (detached)
REM This allows programmatic access via HTTP API

set COMFYUI_PATH=C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI
set PYTHON_PATH=C:\Users\jrjen\comfy\.venv\Scripts\python.exe
set LOG_FILE=C:\Users\jrjen\comfyui_server.log

echo Starting ComfyUI server in background...
echo Log file: %LOG_FILE%

cd /d %COMFYUI_PATH%
start /b "" %PYTHON_PATH% main.py --listen 0.0.0.0 --port 8188 > %LOG_FILE% 2>&1

echo ComfyUI started. Check %LOG_FILE% for output.
