$ErrorActionPreference = 'Stop'
$env:AGENT_COURSE_ENV = Join-Path $PSScriptRoot '.env'
if (!(Test-Path -LiteralPath $env:AGENT_COURSE_ENV)) { throw 'Copy .env.example to .env and configure credentials first.' }
$agentPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $agentPython)) { throw 'Create .venv and install requirements.txt first.' }
Push-Location (Join-Path $PSScriptRoot 'agent/backend')
try { & $agentPython -m uvicorn main:app --host 127.0.0.1 --port 8000 } finally { Pop-Location }
