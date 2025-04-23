@echo off
echo Activating virtual environment...
powershell -ExecutionPolicy Bypass -Command "& '.\.venv\Scripts\activate.ps1'"
echo Virtual environment activated. You can now run Django commands.