@echo off

REM Set to "gpt" or "ollama"
SET LLM_BACKEND=ollama

echo Starting robot control...
start "Robot Control" py -3.7 robot_control.py
echo Starting voice control...
py -3.14 voice_control\main.py
