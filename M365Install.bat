@echo off
setlocal enabledelayedexpansion

:: Create temp directory
set "TEMP_DIR=%TEMP%\M365Install"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: Step 1: Download PowerShell 7 installer
set "PS7_URL=https://github.com/PowerShell/PowerShell/releases/download/v7.4.2/PowerShell-7.4.2-win-x64.msi"
set "PS7_INSTALLER=%TEMP_DIR%\PowerShell7.msi"
curl -L -o "%PS7_INSTALLER%" "%PS7_URL%" >nul 2>&1

:: Step 2: Install PowerShell 7 silently
msiexec /i "%PS7_INSTALLER%" /quiet /norestart >nul 2>&1

:: Step 3: Create PowerShell script for Microsoft 365 installation
set "M365_SCRIPT=%TEMP_DIR%\InstallM365.ps1"
(
echo # Define variables
echo $downloadUrl = "https://go.microsoft.com/fwlink/?linkid=2264705&clcid=0x409&culture=en-us&country=us"
echo $tempDir = "$env:TEMP\M365Install"
echo $installerPath = "$tempDir\Setup.exe"
echo.
echo # Create temp directory if it doesn't exist
echo if (-not (Test-Path $tempDir)) {
echo     New-Item -ItemType Directory -Path $tempDir ^| Out-Null
echo }
echo.
echo # Download the Microsoft 365 installer
echo Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
echo.
echo # Run the installer silently
echo Start-Process -FilePath $installerPath -ArgumentList "/quiet /norestart" -Wait -WindowStyle Hidden
echo.
echo # Clean up
echo Remove-Item -Path "$tempDir\Setup.exe" -Force
) > "%M365_SCRIPT%"

:: Step 4: Run the Microsoft 365 installation using PowerShell 7
set "PWSH_PATH=%ProgramFiles%\PowerShell\7\pwsh.exe"
if exist "%PWSH_PATH%" (
    "%PWSH_PATH%" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%M365_SCRIPT%" >nul 2>&1
)

:: Step 5: Uninstall PowerShell 7 silently
:: Find the Product Code for PowerShell 7
for /f "tokens=2 delims={}" %%a in ('wmic product where "Name like 'PowerShell 7%%'" get IdentifyingNumber ^| find "{"') do (
    set "PRODUCT_CODE={%%a}"
)
if defined PRODUCT_CODE (
    msiexec /x "%PRODUCT_CODE%" /quiet /norestart >nul 2>&1
)

:: Step 6: Clean up
rd /s /q "%TEMP_DIR%" >nul 2>&1

endlocal
exit /b 0