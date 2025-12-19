# main.py (支援雙模式)
import os
import json
import typer
from typing_extensions import Annotated

from scripts.health_check import check_and_start_ollama
from scripts.inbox_agent import process_inbox_item, get_content_from_url, get_text_from_image
from scripts.knowledge_agent import create_knowledge_node
from scripts.notion_handler import (
    create_notion_page, format_inbox_properties, format_knowledge_properties,
    query_notion_database, update_notion_page_status, get_page_content_as_text, build_date_filter, format_review_properties
)
from datetime import date
from scripts.review_agent import generate_periodic_review
from scripts.email_handler import send_email, format_knowledge_node_as_html, format_review_as_html

CONFIG_FILE = 'config.json'
app = typer.Typer(help="JimLocalBrain - 本地 AI 外腦 + 知識庫系統")

def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except FileNotFoundError:
        print(f"❌ 錯誤：找不到設定檔 {CONFIG_FILE}。")
        raise typer.Exit(code=1)
    except json.JSONDecodeError:
        print(f"❌ 錯誤：設定檔 {CONFIG_FILE} 格式不正確。")
        raise typer.Exit(code=1)

CONFIG = load_config()

# 如果是本地模式，才執行健康檢查
if CONFIG.get("LLM_PROVIDER", "local") == "local":
    local_api_url = CONFIG.get("LOCAL_CONFIG", {}).get("LLM_API_BASE_URL", "http://localhost:11434")
    if not check_and_start_ollama(local_api_url):
        print("❌ 無法繼續執行，程式即將退出。")
        raise typer.Exit(code=1)

def process_and_save_content(raw_content: str, url: str = None, source_type: str = None):
    """後端處理與儲存的核心邏輯"""
    if not raw_content or not raw_content.strip():
        print("⚠️ 內容為空，已跳過處理。")
        return

    print("🤖 正在使用 AI 進行智能處理...")
    processed_data = process_inbox_item(raw_content, CONFIG)
    if not processed_data:
        print("⚠️ AI 智能處理失敗。原始筆記仍會被保存。")
        processed_data = {}

    # 將 source_type 傳遞下去
    properties = format_inbox_properties(processed_data, raw_content, url, source_type=source_type)
    
    # 將 raw_content 作為 page_content 傳遞
    if create_notion_page(CONFIG['NOTION_TOKEN'], CONFIG['INBOX_DB_ID'], properties, page_content=raw_content):
        print("✅ 成功新增至 Notion Inbox！")
    else:
        print("❌ 新增至 Notion Inbox 失敗。")

@app.command(name="add")
def run_add(content: str = typer.Argument(..., help="要新增的文字內容")):
    """新增一條文字筆記或靈感至 Inbox。"""
    print("\n--- 🚀 正在新增文字筆記 ---")
    # 傳遞 source_type='text'
    process_and_save_content(content, source_type='text')

@app.command(name="add-url")
def run_add_url(url: str = typer.Argument(..., help="要抓取和新增的網址")):
    """從 URL 抓取內容並新增至 Inbox。"""
    print(f"\n--- 🚀 正在從 URL 新增: {url} ---")
    content = get_content_from_url(url)
    if content:
        # 傳遞 source_type='url'
        process_and_save_content(content, url=url, source_type='url')
    else:
        print("❌ 無法從該網址抓取內容。")

@app.command(name="add-img")
def run_add_image(image_path: str = typer.Argument(..., help="要進行 OCR 的圖片路徑")):
    """從圖片提取文字並新增至 Inbox。"""
    print(f"\n--- 🚀 正在從圖片新增: {image_path} ---")
    content = get_text_from_image(image_path)
    if content:
        # 傳遞 source_type='image'
        process_and_save_content(content, source_type='image')
    else:
        print("❌ 無法從圖片中提取文字。")

# ... (main.py 的其餘部分保持不變) ...
@app.command(name="synthesis")
def run_knowledge_synthesis():
    """將 Inbox 中『New』狀態的項目，轉換為知識節點。"""
    print("\n--- 🚀 開始知識合成 ---")
    filter_payload = {"property": "Status", "select": {"equals": "New"}}
    new_items = query_notion_database(CONFIG['NOTION_TOKEN'], CONFIG['INBOX_DB_ID'], filter_payload, CONFIG.get("DEBUG_MODE", False))

    if not new_items:
        print("✅ Inbox 中沒有需要合成的新項目。")
        return

    for item in new_items:
        page_id = item['id']
        print(f"   - 正在處理項目: {page_id}")
        
        # --- 核心修改：傳入 CONFIG['NOTION_TOKEN'] ---
        content_to_process, metadata = get_page_content_as_text(CONFIG['NOTION_TOKEN'], item)
        # -----------------------------------------------
        
        if not content_to_process.strip():
            print(f"   - 項目 {page_id} 內容為空，跳過。")
            continue

        knowledge_data = create_knowledge_node(content_to_process, CONFIG)
        if not knowledge_data:
            print(f"   - 知識節點生成失敗，跳過項目 {page_id}"); continue
        
        # --- 核心修改：傳遞 metadata 字典，而不是 url ---
        properties = format_knowledge_properties(knowledge_data, metadata=metadata)
        # -----------------------------------------------
        
        if create_notion_page(CONFIG['NOTION_TOKEN'], CONFIG['KNOWLEDGE_DB_ID'], properties):
            update_notion_page_status(CONFIG['NOTION_TOKEN'], page_id, "Processed")
            
            # --- 新增：發送 Email ---
            email_subject, email_body = format_knowledge_node_as_html(knowledge_data, metadata)
            send_email(f"New Knowledge Node: {email_subject}", email_body, CONFIG)
            # ------------------------     
        
    print("\n--- ✅ 知識合成完成 ---\n")
 
@app.command(name="review")
def run_periodic_review(
    period: str = typer.Option("weekly", "--period", "-p", help="回顧的期間: weekly, monthly, quarterly")
):
    """從 Knowledge Base 提取指定期間的筆記，並生成趨勢分析報告。"""
    print(f"\n--- 🚀 開始執行 {period} 趨勢分析 ---")
    
    # 1. 建立日期過濾器並獲取筆記
    date_filter = build_date_filter(period)
    notes = query_notion_database(CONFIG['NOTION_TOKEN'], CONFIG['KNOWLEDGE_DB_ID'], date_filter)
    
    if not notes:
        print(f"✅ 在指定期間內沒有找到新的知識節點。")
        return
        
    # 2. 資訊濃縮
    consolidated_notes = []
    for note in notes:
        props = note.get("properties", {})
        title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "")
        core_idea = props.get("Core Idea", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        # --- 核心修改 2：在濃縮文本中加入標記 ---
        note_prefix = ""
        # 檢查標題是否以燈泡 emoji 開頭
        if title.strip().startswith("💡"):
            note_prefix = "[ORIGINAL IDEA] "
        # ------------------------------------
        consolidated_notes.append(f"## {title}\n> {core_idea}\n")
    
    consolidated_text = "\n---\n".join(consolidated_notes)
    
    # 3. 趨勢合成
    review_data = generate_periodic_review(consolidated_text, period, CONFIG)
    
    if not review_data:
        print("❌ 趨勢分析失敗，已終止。")
        return
        
    # 4. 歸檔儲存
    # --- 核心修改：使用新的字典結構來取值 ---
    start_date = date.fromisoformat(date_filter['created_time']['on_or_after'])
    # -----------------------------------------
    end_date = date.today()
    review_properties = format_review_properties(review_data, period, start_date, end_date)
    
    # --- 核心修改：檢查 create_notion_page 的返回值 ---
    result = create_notion_page(
        CONFIG['NOTION_TOKEN'],
        CONFIG['REVIEW_DB_ID'],
        review_properties
    )

    if result:
        print(f"\n--- ✅ {period.capitalize()} 趨勢分析報告已成功生成並儲存至 Notion！ ---\n")
        # --- 新增：發送 Email ---
        email_subject, email_body = format_review_as_html(review_data, period)
        send_email(email_subject, email_body, CONFIG)
        # ------------------------        
    else:
        print(f"\n--- ❌ {period.capitalize()} 趨勢分析報告儲存失敗。請檢查上面的錯誤訊息。 ---\n")
    # ------------------------------------------------- 

if __name__ == "__main__":
    app()
