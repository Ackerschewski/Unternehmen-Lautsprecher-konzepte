$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
& $python -m pip install -e '.[dev]'
$testTemp = '.test_tmp_' + [guid]::NewGuid().ToString('N')
& $python -m pytest --basetemp $testTemp -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw 'Ruff failed' }
& $python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name 'Lautsprecher-Konstruktion_V-02.04.00' --paths 'src' `
    --add-data 'data/library;data/library' `
    --hidden-import 'matplotlib.backends.backend_qtagg' `
    'src/lautsprecher_konstruktion/app.py'
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }

# PyInstaller can collect a third-party ICU build as _internal/icuuc.dll.
# Qt's Windows binaries use the unsuffixed ICU API exported by Windows itself;
# the collected ICU build exports version-suffixed names and breaks QtCore.
$bundledIcu = Join-Path $PSScriptRoot '..\dist\Lautsprecher-Konstruktion_V-02.04.00\_internal\icuuc.dll'
if (Test-Path -LiteralPath $bundledIcu) {
    & $python -c 'import pathlib,sys; pathlib.Path(sys.argv[1]).unlink()' $bundledIcu
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove incompatible ICU DLL' }
}

$appExe = Join-Path $PSScriptRoot '..\dist\Lautsprecher-Konstruktion_V-02.04.00\Lautsprecher-Konstruktion_V-02.04.00.exe'
$previousQtPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = 'offscreen'
try {
    $appProcess = Start-Process -FilePath $appExe -ArgumentList '--smoke-assistant' -PassThru -WindowStyle Hidden
    if (-not $appProcess.WaitForExit(60000)) {
        $appProcess.Kill()
        throw 'Packaged application smoke test timed out'
    }
    if ($appProcess.ExitCode -ne 0) { throw 'Packaged application smoke test failed' }
} finally {
    $env:QT_QPA_PLATFORM = $previousQtPlatform
}

Write-Host "Build complete."


