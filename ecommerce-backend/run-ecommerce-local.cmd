@echo off
cd /d "%~dp0"
where mvn.cmd >nul 2>nul
if errorlevel 1 (
  echo Maven is not available in PATH. Please install Maven or use the project Docker command.
  exit /b 1
)

mvn.cmd spring-boot:run -Dspring-boot.run.profiles=test -Dspring-boot.run.arguments=--server.port=8081 > target\ecommerce-run.log 2> target\ecommerce-run.err.log
