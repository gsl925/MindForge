# set_password.py
import keyring
import getpass

# 定義服務名稱和用戶名，這將作為密碼的索引
SERVICE_NAME = "MindForge"
USERNAME = "ckchuanginchina@gmail.com" # 請換成您的 Gmail

# 獲取密碼
app_password = getpass.getpass(f"請輸入 {USERNAME} 的 16 位應用程式密碼: ")

# 將密碼安全地存儲到系統的密碼管理器中
keyring.set_password(SERVICE_NAME, USERNAME, app_password)

print(f"✅ 密碼已成功為 {SERVICE_NAME} 儲存！您現在可以刪除此腳本了。")
