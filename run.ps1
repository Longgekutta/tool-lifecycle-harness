# PowerShell 启动器
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 自动定位 Python
$PythonExe = "python"
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Test-Path "D:\DevTools\Python\Python312\python.exe") {
    $PythonExe = "D:\DevTools\Python\Python312\python.exe"
}

& $PythonExe "$ScriptDir\main.py" @args
