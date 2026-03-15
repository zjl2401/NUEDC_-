@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 当前目录: %CD%
set "PYTHONPATH=%~dp0"
echo 运行纯软件模拟...
echo 按 Q 退出
echo.
python main.py --mode simulate
if errorlevel 1 (
    echo.
    echo 若提示缺少模块，请执行: pip install -r requirements.txt
    pause
)
