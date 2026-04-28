@echo off
rem --- 強制使用 UTF-8 編碼以顯示中文 ---
chcp 65001 > nul

TITLE MindForge Home UI
rem --- 設定專案路徑 ---
set "PROJECT_DIR=D:\_Personal\_Coding\_Python\JimLocalBrain"

rem --- 設定 Python 環境變數以強制輸出 UTF-8 ---
set PYTHONUTF8=1

rem --- 切換到專案目錄 ---
cd /d "%PROJECT_DIR%"

rem --- 啟動虛擬環境 ---
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] 找不到虛擬環境 venv，請確認專案目錄是否正確。
    pause
    exit /b
)

rem --- 執行 Streamlit ---
echo 🚀 正在啟動 MindForge UI (Home.py)...
streamlit run Home.py

rem --- 如果程式異常關閉，保留視窗顯示錯誤訊息 ---
pause
