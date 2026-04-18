@echo off
setlocal

if not defined KAGGLE_API_TOKEN (
  for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$t=[Environment]::GetEnvironmentVariable('KAGGLE_API_TOKEN','User'); if($t){$t}"`) do set "KAGGLE_API_TOKEN=%%i"
)

if not defined KAGGLE_API_TOKEN (
  echo KAGGLE_API_TOKEN is not set. Create a Kaggle API token and store it as a user environment variable. 1>&2
  exit /b 1
)

where kaggle.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  kaggle.exe %*
  exit /b %ERRORLEVEL%
)

set "KAGGLE_EXE=%LOCALAPPDATA%\Programs\Python\Python313\Scripts\kaggle.exe"
if exist "%KAGGLE_EXE%" (
  "%KAGGLE_EXE%" %*
  exit /b %ERRORLEVEL%
)

echo Kaggle CLI was not found on PATH or at %KAGGLE_EXE%. 1>&2
exit /b 1
