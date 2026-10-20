@echo off
cd /d "%~dp0"
echo Starting AURA Twin. Open http://localhost:4173 in your browser.
node --env-file-if-exists=.env.auth.local server.mjs
pause
