# DoGiaKD Build Tool
# Chay: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "         DoGiaKD Build Tool" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Kiem tra Python ---
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[LOI] Khong tim thay Python. Vui long cai dat Python 3.10+" -ForegroundColor Red
    pause; exit 1
}

# --- Lay duong dan site-packages tu dong ---
$SITE_PACKAGES = python -c "import site; print([p for p in site.getsitepackages() if 'site-packages' in p][0])" 2>$null
if (-not $SITE_PACKAGES) {
    Write-Host "[LOI] Khong the xac dinh duong dan site-packages." -ForegroundColor Red
    pause; exit 1
}
Write-Host "[INFO] Site-packages: $SITE_PACKAGES"

# --- Kiem tra PyInstaller ---
$ErrorActionPreference = "Continue"
python -c "import PyInstaller" 2>$null
$ErrorActionPreference = "Stop"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[CANH BAO] PyInstaller chua duoc cai dat. Dang cai dat..." -ForegroundColor Yellow
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[LOI] Khong the cai dat PyInstaller." -ForegroundColor Red
        pause; exit 1
    }
}

# --- Kiem tra file spec ---
if (-not (Test-Path "DoGiaKD.spec")) {
    Write-Host "[LOI] Khong tim thay file DoGiaKD.spec trong thu muc hien tai." -ForegroundColor Red
    pause; exit 1
}

# --- Doc version ---
$VERSION = ""
if (Test-Path "version.txt") {
    $VERSION = (Get-Content "version.txt" -Raw).Trim()
    Write-Host "[INFO] Phien ban: $VERSION"
} else {
    Write-Host "[CANH BAO] Khong tim thay version.txt" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[BUOC 1/3] Dang build voi PyInstaller..." -ForegroundColor Green
Write-Host "--------------------------------------------"
python -m PyInstaller DoGiaKD.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "[LOI] PyInstaller build that bai." -ForegroundColor Red
    pause; exit 1
}
Write-Host "[OK] Build thanh cong." -ForegroundColor Green

Write-Host ""
Write-Host "[BUOC 2/3] Dang copy thu vien pywinauto va comtypes..." -ForegroundColor Green
Write-Host "--------------------------------------------"

$DIST_DIR = Join-Path $ScriptDir "dist\DoGiaKD"

if (-not (Test-Path $DIST_DIR)) {
    Write-Host "[LOI] Thu muc dist\DoGiaKD khong ton tai. Build co the da that bai." -ForegroundColor Red
    pause; exit 1
}

# Copy pywinauto
$pywinautoSrc = Join-Path $SITE_PACKAGES "pywinauto"
$pywinautoDst = Join-Path $DIST_DIR "pywinauto"
if (Test-Path $pywinautoSrc) {
    Copy-Item $pywinautoSrc $pywinautoDst -Recurse -Force
    Write-Host "[OK] Da copy pywinauto" -ForegroundColor Green
} else {
    Write-Host "[CANH BAO] Khong tim thay pywinauto. Dang cai dat..." -ForegroundColor Yellow
    pip install pywinauto
    if (Test-Path $pywinautoSrc) {
        Copy-Item $pywinautoSrc $pywinautoDst -Recurse -Force
        Write-Host "[OK] Da cai dat va copy pywinauto" -ForegroundColor Green
    } else {
        Write-Host "[LOI] Khong the tim thay pywinauto sau khi cai dat." -ForegroundColor Red
        pause; exit 1
    }
}

# Copy comtypes
$comtypesSrc = Join-Path $SITE_PACKAGES "comtypes"
$comtypesDst = Join-Path $DIST_DIR "comtypes"
if (Test-Path $comtypesSrc) {
    Copy-Item $comtypesSrc $comtypesDst -Recurse -Force
    Write-Host "[OK] Da copy comtypes" -ForegroundColor Green
} else {
    Write-Host "[CANH BAO] Khong tim thay comtypes. Dang cai dat..." -ForegroundColor Yellow
    pip install comtypes
    if (Test-Path $comtypesSrc) {
        Copy-Item $comtypesSrc $comtypesDst -Recurse -Force
        Write-Host "[OK] Da cai dat va copy comtypes" -ForegroundColor Green
    } else {
        Write-Host "[LOI] Khong the tim thay comtypes sau khi cai dat." -ForegroundColor Red
        pause; exit 1
    }
}

Write-Host ""
Write-Host "[BUOC 3/3] Kiem tra ket qua build..." -ForegroundColor Green
Write-Host "--------------------------------------------"

$exePath = Join-Path $DIST_DIR "DoGiaKD.exe"
if (Test-Path $exePath) {
    Write-Host "[OK] File DoGiaKD.exe da duoc tao thanh cong." -ForegroundColor Green
    Write-Host "[INFO] Vi tri: $exePath"
} else {
    Write-Host "[LOI] Khong tim thay DoGiaKD.exe trong thu muc dist." -ForegroundColor Red
    pause; exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   BUILD HOAN TAT THANH CONG!" -ForegroundColor Cyan
if ($VERSION) { Write-Host "   Phien ban: $VERSION" -ForegroundColor Cyan }
Write-Host "   Output: dist\DoGiaKD\" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
pause
