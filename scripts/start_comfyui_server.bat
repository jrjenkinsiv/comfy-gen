@echo off
REM Start ComfyUI server in API mode on moira
REM This allows programmatic access via HTTP API

set COMFYUI_PATH=C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI
set PYTHON_PATH=C:\Users\jrjen\comfy\.venv\Scripts\python.exe

echo Starting ComfyUI server...
echo ComfyUI path: %COMFYUI_PATH%
echo Python path: %PYTHON_PATH%

cd /d %COMFYUI_PATH%
%PYTHON_PATH% main.py --listen 0.0.0.0 --port 8188
