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

def _process_and_save_content(raw_content: str, url: str = None):
    if not raw_content or not raw_content.strip():
        print("⚠️ 內容為空，已跳過處理。"); return

    # 將整個 CONFIG 物件傳遞下去
    processed_data = process_inbox_item(raw_content, CONFIG)
    
    if not processed_data:
        print("\n⚠️ AI 智能處理失敗。")
        print("   不過別擔心，您的原始筆記和來源 URL (如有) 仍會被保存到 Notion。")
        processed_data = {}
        
    properties = format_inbox_properties(processed_data, raw_content, url)
    create_notion_page(CONFIG['NOTION_TOKEN'], CONFIG['INBOX_DB_ID'], properties)

@app.command(name="add")
def add_text(text: Annotated[str, typer.Argument(help="要直接新增的文本內容")]):
    _process_and_save_content(text, url=None)

@app.command(name="add-url")
def add_url(url: Annotated[str, typer.Argument(help="要抓取並新增的網頁 URL")]):
    raw_content = get_content_from_url(url)
    _process_and_save_content(raw_content, url=url)

# ... (main.py 的其餘部分保持不變) ...
@app.command(name="synthesis")
def run_knowledge_synthesis():
    print("\n--- 🚀 開始知識合成 ---")
    filter_payload = {"property": "Status", "select": {"equals": "New"}}
    new_items = query_notion_database(CONFIG['NOTION_TOKEN'], CONFIG['INBOX_DB_ID'], filter_payload)
    if not new_items:
        print("✅ Inbox 中沒有需要合成的新項目。"); return
    
    print(f"找到 {len(new_items)} 個新項目需要處理。")
    for item in new_items:
        page_id = item['id']
        content_to_process, source_url = get_page_content_as_text(item)
        print(f"\n🧠 正在處理項目: {content_to_process[:80]}...")
        
        # 將整個 CONFIG 物件傳遞下去
        knowledge_data = create_knowledge_node(content_to_process, CONFIG)
        
        if not knowledge_data:
            print(f"   - 知識節點生成失敗，跳過項目 {page_id}"); continue
            
        properties = format_knowledge_properties(knowledge_data, url=source_url)
        create_notion_page(CONFIG['NOTION_TOKEN'], CONFIG['KNOWLEDGE_DB_ID'], properties)
        update_notion_page_status(CONFIG['NOTION_TOKEN'], page_id, "Processed")
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
    else:
        print(f"\n--- ❌ {period.capitalize()} 趨勢分析報告儲存失敗。請檢查上面的錯誤訊息。 ---\n")
    # ------------------------------------------------- 

if __name__ == "__main__":
    app()
