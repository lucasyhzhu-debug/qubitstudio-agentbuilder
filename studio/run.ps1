# studio/run.ps1 — Windows convenience shim; the real launcher is cross-platform.
$repo = Split-Path -Parent $PSScriptRoot
python -m studio @args
