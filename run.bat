@echo off
cd /d "%~dp0"
call conda activate hupu
python main.py
