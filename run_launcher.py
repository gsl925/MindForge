# run_launcher.py

import subprocess
import os
import sys
import webbrowser
import time

def main():
    """
    這是一個啟動器腳本，它的職責是：
    1. 找到打包後的 streamlit.exe 和 Home.py 的路徑。
    2. 使用 subprocess 在背景啟動一個新的 streamlit 伺服器進程。
    3. 打開瀏覽器指向 streamlit 的 URL。
    4. 等待使用者關閉主控台視窗，然後清理背景進程。
    """
    # 獲取主執行檔 (.exe) 所在的目錄
    base_dir = os.path.dirname(sys.executable)

    # 構造 streamlit.exe 和 Home.py 的絕對路徑
    # PyInstaller 會將 streamlit 的可執行腳本放在根目錄
    streamlit_exe_path = os.path.join(base_dir, 'streamlit.exe')
    home_py_path = os.path.join(base_dir, 'Home.py')

    # 檢查必要的檔案是否存在
    if not os.path.exists(streamlit_exe_path):
        print(f"錯誤：找不到 streamlit.exe，路徑: {streamlit_exe_path}")
        time.sleep(10)
        return
    if not os.path.exists(home_py_path):
        print(f"錯誤：找不到 Home.py，路徑: {home_py_path}")
        time.sleep(10)
        return

    # 準備要執行的命令
    command = [
        streamlit_exe_path,
        "run",
        home_py_path,
        "--server.headless", "true",  # 以無頭模式運行，主程式會負責開瀏覽器
        "--server.port", "8501"       # 固定端口
    ]

    print("正在啟動 MindForge 伺服器...")
    print(f"執行命令: {' '.join(command)}")

    # 在背景啟動 Streamlit 伺服器進程
    # 使用 CREATE_NO_WINDOW 標誌來隱藏 streamlit 自己的黑視窗 (僅限 Windows)
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
        # 等待背景進程結束 (例如，如果它自己崩潰了)
        # 或者等待使用者關閉這個主控台視窗
        server_process.wait()
    except KeyboardInterrupt:
        # 如果使用者在主控台按 Ctrl+C
        print("偵測到 Ctrl+C，正在關閉伺服器...")
    finally:
        # 確保在主程式退出時，背景的 streamlit 伺服器也被終止
        print("正在終止 MindForge 伺服器...")
        server_process.terminate()
        server_process.wait()
        print("伺服器已關閉。")

if __name__ == "__main__":
    main()
