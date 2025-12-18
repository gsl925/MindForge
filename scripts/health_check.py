# scripts/health_check.py
import subprocess
import requests
import time
import os
import sys # 導入 sys 模組以檢查平台

def check_and_start_ollama(api_base_url: str, timeout: int = 30):
    """
    檢查 Ollama 服務是否在運行，如果沒有，則使用跨平台、無彈窗的方式啟動它。
    """
    print("🩺 正在檢查 Ollama 服務狀態...")
    
    try:
        requests.get(api_base_url, timeout=2)
        print("✅ Ollama 服務已在運行。")
        return True
    except requests.exceptions.ConnectionError:
        print("⚠️ Ollama 服務未運行。正在嘗試啟動...")
        
        try:
            # --- 採用您提供的專業跨平台啟動邏輯 ---
            # 在 Windows 上，設定 creationflags 以避免彈出黑色的命令提示字元視窗
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # 使用 Popen 在背景啟動 'ollama serve'
            # 將 stdout 和 stderr 重定向到 DEVNULL，以避免 Ollama 的日誌佔滿我們的終端機
            proc = subprocess.Popen(
                ["ollama", "serve"], 
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"🚀 已發送啟動 Ollama 服務的指令 (PID: {proc.pid})...")
            # -----------------------------------------

        except FileNotFoundError:
            print("❌ 'ollama' 指令未找到。請確保 Ollama 已安裝並在系統 PATH 中。")
            return False
        
        print(f"   ...將等待最多 {timeout} 秒讓服務上線...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(2)
            try:
                requests.get(api_base_url, timeout=2)
                print("✅ Ollama 服務已成功啟動！")
                return True
            except requests.exceptions.ConnectionError:
                continue
        
        print(f"❌ 在 {timeout} 秒內，Ollama 服務未能成功啟動。請手動檢查。")
        return False
