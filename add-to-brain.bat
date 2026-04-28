@echo off
rem --- 強制使用 UTF-8 編碼以顯示中文 ---
chcp 65001 > nul

rem =================================================================
rem  JimLocalBrain Flow Launcher 啟動器
rem =================================================================

rem --- 1. 設定您的專案路徑 (這是唯一需要修改的地方) ---
set "PROJECT_DIR=D:\_Personal\_Coding\_Python\JimLocalBrain"

rem --- 2. 啟動 Python 虛擬環境 ---
call %PROJECT_DIR%\venv\Scripts\activate

rem --- 3. 切換到專案目錄 ---
cd /d %PROJECT_DIR%

rem --- 4. 執行主程式，並將所有參數傳遞過去 ---
echo.
echo 🚀 正在執行 JimLocalBrain，請稍候...
echo    - 傳入參數: %*
echo --------------------------------------------------
python main.py %*

rem --- 5. 執行完畢後暫停，以便查看輸出 ---
echo --------------------------------------------------
echo ✅ 處理完成，按任意鍵關閉此視窗...
pause > nul
