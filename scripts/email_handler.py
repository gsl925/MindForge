# scripts/email_handler.py
import smtplib
# import getpass  <-- 不再需要 getpass
import keyring    # <-- 導入 keyring
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject: str, html_body: str, config: dict):
    """
    發送一封 HTML 格式的 Email。
    """
    email_config = config.get("EMAIL_CONFIG", {})
    if not email_config.get("enabled", False):
        return # 如果 Email 功能未啟用，直接返回

    sender = email_config.get("sender_email")
    receiver = email_config.get("receiver_email")
    smtp_server = email_config.get("smtp_server")
    smtp_port = email_config.get("smtp_port")

    if not all([sender, receiver, smtp_server, smtp_port]):
        print("⚠️ Email 設定不完整，已跳過發送。")
        return

    try:
        # --- 核心修改：從 keyring 獲取密碼 ---
        SERVICE_NAME = "MindForge" # 必須與 set_password.py 中的一致
        password = keyring.get_password(SERVICE_NAME, sender)

        if not password:
            print(f"❌ 未能在系統密碼管理器中找到 {sender} 的密碼。")
            print(f"   請先運行一次性的 `set_password.py` 腳本來儲存密碼。")
            return
        # ------------------------------------

        # 建立郵件物件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver

        # 附加 HTML 內容
        part = MIMEText(html_body, 'html')
        msg.attach(part)

        # 連接並發送
        print(f"📧 正在連接到 {smtp_server} 並嘗試發送郵件...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # 啟用 TLS 加密
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        
        print(f"✅ Email 已成功發送至 {receiver}！")

    except smtplib.SMTPAuthenticationError:
        print("❌ Email 認證失敗！請檢查您的 Email 地址和密碼（或應用程式密碼）是否正確。")
    except Exception as e:
        print(f"❌ 發送 Email 時發生錯誤: {e}")

def format_knowledge_node_as_html(data: dict, metadata: dict) -> tuple[str, str]:
    """將知識節點格式化為 HTML，並返回標題和內容。"""
    title = data.get('title', 'Untitled Knowledge Node')
    if any(tag.get("name") == "Original Thought" for tag in metadata.get("tags", [])):
        title = f"💡 {title}"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            p {{ color: #333; }}
            ul {{ list-style-type: disc; margin-left: 20px; }}
            .container {{ max-width: 700px; margin: 20px auto; padding: 20px; border: 1px solid #eee; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <h2>Core Idea</h2>
            <p>{data.get('core_idea', 'N/A')}</p>
            <h2>Key Insights</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in data.get('key_insights', []))}</ul>
            <h2>Use Cases</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in data.get('use_cases', []))}</ul>
            <h2>Notes</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in data.get('notes', []))}</ul>
        </div>
    </body>
    </html>
    """
    return title, html

def format_review_as_html(review_data: dict, period: str) -> tuple[str, str]:
    """將趨勢報告格式化為 HTML，並返回標題和內容。"""
    title = f"📊 {period.capitalize()} Trend Review"
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            p, li {{ color: #333; }}
            ul {{ list-style-type: disc; margin-left: 20px; }}
            .container {{ max-width: 700px; margin: 20px auto; padding: 20px; border: 1px solid #eee; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <h2>Overall Summary</h2>
            <p>{review_data.get('overall_summary', 'N/A')}</p>
            <h2>Key Trends</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in review_data.get('key_trends', []))}</ul>
            <h2>Emerging Ideas</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in review_data.get('emerging_ideas', []))}</ul>
            <h2>Actionable Insights</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in review_data.get('actionable_insights', []))}</ul>
            <h2>Unanswered Questions</h2>
            <ul>{''.join(f"<li>{item}</li>" for item in review_data.get('unanswered_questions', []))}</ul>
        </div>
    </body>
    </html>
    """
    return title, html
