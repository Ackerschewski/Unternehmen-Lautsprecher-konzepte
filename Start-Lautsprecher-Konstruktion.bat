@echo off
setlocal
cd /d "%~dp0"
title Lautsprecher Konstruktion

rem Needs Python 3.12 or newer (https://www.python.org/downloads/). First start installs the program (internet needed once).
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python 3.12 oder neuer wurde nicht gefunden.
  echo Bitte von https://www.python.org/downloads/ installieren ^(Haken "Add python.exe to PATH" setzen^) und diese Datei erneut starten.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Erster Start: Umgebung wird eingerichtet ...
  %PY% -m venv .venv || (echo Umgebung konnte nicht erstellt werden. & pause & exit /b 1)
)
if not exist ".venv\installiert.txt" (
  echo Programm und Bibliotheken werden installiert ^(einmalig, einige Minuten^) ...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -e . || (echo Installation fehlgeschlagen. Internetverbindung pruefen. & pause & exit /b 1)
  echo ok> ".venv\installiert.txt"
)

".venv\Scripts\python.exe" -m lautsprecher_konstruktion.app
if errorlevel 1 (
  echo.
  echo Das Programm wurde mit einem Fehler beendet. Protokoll: %%LOCALAPPDATA%%\LautsprecherKonstruktion\logs
  pause
)
