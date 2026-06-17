# Tauri 一键打包脚本
# 用法：powershell -ExecutionPolicy Bypass -File build.ps1
[CmdletBinding()]
param(
    [switch]$SkipInstall,   # 跳过 npm install
    [switch]$SkipBuild,     # 跳过前端 build（只跑 tauri build）
    [switch]$BundleOnly     # 不做类型检查（快）
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
Set-Location $root

function Write-Header($text) {
    Write-Host ""
    Write-Host "==[ $text ]==" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Assert-Tool($name, $checkCmd) {
    try {
        $version = & $checkCmd 2>&1
        if ($LASTEXITCODE -ne 0) { throw "exit=$LASTEXITCODE" }
        Write-Host "[OK] $name : $version" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $name not found" -ForegroundColor Red
        Write-Host "       Fix: $checkCmd" -ForegroundColor Yellow
        exit 1
    }
}

Write-Header "Pre-flight check"
Assert-Tool "node" { node --version }
Assert-Tool "npm" { npm --version }
Assert-Tool "rustc" { rustc --version }
Assert-Tool "cargo" { cargo --version }

# MSVC 检测
$msvcFound = $false
$vswhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vswhere) {
    $paths = & $vswhere -all -property installationPath 2>$null
    foreach ($p in $paths) {
        if ($p -and (Test-Path "$p\VC\Tools\MSVC")) { $msvcFound = $true; break }
    }
}
# 也试 C:\BuildTools
if (-not $msvcFound -and (Test-Path "C:\BuildTools\VC\Tools\MSVC")) { $msvcFound = $true }
if (-not $msvcFound) {
    Write-Host "[FAIL] MSVC BuildTools not found" -ForegroundColor Red
    Write-Host "       Download: https://aka.ms/vs/17/release/vs_buildtools.exe" -ForegroundColor Yellow
    Write-Host "       Install with: vs_buildtools.exe --quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --installPath C:\BuildTools" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] MSVC BuildTools found" -ForegroundColor Green

if (-not $SkipInstall) {
    Write-Header "npm install"
    npm install
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

if (-not $SkipBuild) {
    Write-Header "Frontend build (vue-tsc + vite)"
    if ($BundleOnly) {
        # 跳过类型检查（快）
        npx vite build
    } else {
        npm run build
    }
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Write-Header "Tauri build (Rust + bundle)"
npx tauri build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Header "Done"
$bundle = Join-Path $root "src-tauri\target\release\bundle"
if (Test-Path $bundle) {
    Get-ChildItem -Path $bundle -Recurse -File -Filter "*.msi" | ForEach-Object {
        Write-Host ("[MSI] {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB)) -ForegroundColor Green
    }
    Get-ChildItem -Path $bundle -Recurse -File -Filter "*-setup.exe" | ForEach-Object {
        Write-Host ("[EXE] {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB)) -ForegroundColor Green
    }
}
