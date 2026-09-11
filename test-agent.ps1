$ErrorActionPreference = 'Stop'
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $PSScriptRoot 'agent'
$agentPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
Push-Location (Join-Path $PSScriptRoot 'agent/backend')
try {
    & $agentPython -m unittest discover -s tests
    $testExitCode = $LASTEXITCODE
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
}
exit $testExitCode
