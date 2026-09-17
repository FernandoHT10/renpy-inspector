# PowerShell build script for Ren'Py Inspector standalone executable

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Ren'Py Inspector — Windows Standalone Build " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectDir

Write-Host "Compiling with Python & PyInstaller..." -ForegroundColor Yellow
python scripts/build_windows.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nCompilation completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nCompilation failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
