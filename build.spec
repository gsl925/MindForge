# run_launcher.py (v12 - 自給自足模式)

import subprocess
import os
import sys
import webbrowser
import time

def main():
    """
    這是一個自給自足的啟動器，它的職責是：
    1. 找到打包環境內部的 python.exe 和 Home.py 的路徑。
    2. 使用內部的 python.exe，以模組模式 (-m) 在背景啟動 streamlit。
    3. 打開瀏覽器，等待並管理背景進程。
    """
    # 獲取主執行檔 (MindForge.exe) 所在的目錄
    base_dir = os.path.dirname(sys.executable)

    # --- 【核心修改】: 構造內部 python.exe 的路徑 ---
    # PyInstaller 打包後，通常會有一個 python.exe 在根目錄或子目錄
    # 我們假設它在根目錄，這是最常見的情況
    python_exe_path = os.path.join(base_dir, 'python.exe')
    home_py_path = os.path.join(base_dir, 'Home.py')

    # 檢查必要的檔案是否存在
    if not os.path.exists(python_exe_path):
        # 如果根目錄沒有，嘗試在 Scripts 子目錄找 (備用方案)
        python_exe_path = os.path.join(base_dir, 'Scripts', 'python.exe')
        if not os.path.exists(python_exe_path):
             print(f"致命錯誤：在打包目錄中找不到 python.exe！")
             time.sleep(10)
             return
             
    if not os.path.exists(home_py_path):
        print(f"錯誤：找不到 Home.py，路徑: {home_py_path}")
        time.sleep(10)
        return

    # --- 【核心修改】: 準備全新的、內部化的命令 ---
    command = [
        python_exe_path,
        "-m",           # 以模組方式運行
        "streamlit",
        "run",
        home_py_path,
        "--server.headless", "true",
        "--server.port", "8501"
    ]

    print("正在啟動 MindForge 伺服器 (內部模式)...")
    print(f"執行命令: {' '.join(command)}")

    # 在背景啟動 Streamlit 伺服器進程
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    server_process = subprocess.Popen(command, creationflags=creation_flags)

    # 等待幾秒鐘，確保伺服器有足夠的時間啟動
    time.sleep(5)

    # 打開瀏覽器
    url = "http://localhost:8501"
    print(f"伺服器已啟動，正在打開瀏覽器: {url}")
    webbrowser.open(url)

    print("\nMindForge 正在運行中。關閉此視窗即可終止程式。")

    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("偵測到 Ctrl+C，正在關閉伺服器...")
    finally:
        print("正在終止 MindForge 伺服器...")
        server_process.terminate()
        server_process.wait()
        print("伺服器已關閉。")

if __name__ == "__main__":
    main()
