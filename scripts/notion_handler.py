# scripts/notion_handler.py
import requests
import json
import ast
from datetime import datetime, timedelta, date # 確保在檔案頂部導入

# --- 新增：可重用的輔助函式 ---
def _format_list_content(content) -> str:
    """
    一個通用的清理函式，可以處理字串、列表和"列表形式的字串"。
    將它們統一轉換為帶有項目符號的單一字串。
    """
    if isinstance(content, list):
        # 情況 1: 內容是真正的列表
        return "\n".join([f"• {item}" for item in content])
    
    elif isinstance(content, str):
        # 情況 2: 內容是字串
        stripped_content = content.strip()
        if stripped_content.startswith('[') and stripped_content.endswith(']'):
            try:
                # 嘗試將 "列表形式的字串" 轉換為真正的列表
                content_list = ast.literal_eval(stripped_content)
                if isinstance(content_list, list):
                    return "\n".join([f"• {item}" for item in content_list])
            except (ValueError, SyntaxError):
                # 轉換失敗，當作普通字串處理
                pass
        # 如果不是 "列表形式的字串"，或者轉換失敗，直接返回原始字串
        return content
    
    # 其他情況（如數字等），轉換為字串返回
    return str(content)

# --- create_notion_page, format_inbox_properties, query_notion_database, update_notion_page_status, get_page_content_as_text 保持不變 ---
# ... (這裡省略了未修改的函式，您無需改動它們) ...

def create_notion_page(token: str, database_id: str, properties: dict):
    url = "https://api.notion.com/v1/pages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    payload = {"parent": {"database_id": database_id}, "properties": properties}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print(f"✅ 成功將頁面 '{properties.get('Title', {}).get('title', [{}])[0].get('text', {}).get('content', 'N/A')}' 新增至 Notion！")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 新增 Notion 頁面時發生錯誤: {e}\n   錯誤詳情: {response.text}")
        return None

def format_inbox_properties(data: dict, raw_content: str, url: str = None) -> dict:
    properties = {
        "Title": {"title": [{"text": {"content": data.get("title", "Untitled")}}]},
        "Raw Content": {"rich_text": [{"text": {"content": raw_content[:2000]}}]},
        "Short Summary": {"rich_text": [{"text": {"content": data.get("short_summary", "")}}]},
        "Extended Summary": {"rich_text": [{"text": {"content": data.get("extended_summary", "")}}]},
        "Category": {"select": {"name": data.get("category", "Knowledge")}},
        "Tags": {"multi_select": [{"name": tag} for tag in data.get("tags", [])]},
        "Status": {"select": {"name": "New"}}
    }
    if url:
        properties["URL"] = {"url": url}
    return properties

# --- 核心修改 2：讓 format_knowledge_properties 接收並使用元數據 ---
def format_knowledge_properties(data: dict, metadata: dict) -> dict:
    """將 Knowledge Agent 的輸出和原始元數據格式化為 Notion API 結構。"""
    
    # 處理 AI 生成的內容
    notes_string = _format_list_content(data.get("notes", ""))
    insights_string = _format_list_content(data.get("key_insights", ""))
    use_cases_string = _format_list_content(data.get("use_cases", ""))

    properties = {
        "Title": {"title": [{"text": {"content": data.get("title", "Untitled")}}]},
        "Core Idea": {"rich_text": [{"text": {"content": data.get("core_idea", "")}}]},
        "Notes": {"rich_text": [{"text": {"content": notes_string[:2000]}}]},
        "Key Insights": {"rich_text": [{"text": {"content": insights_string[:2000]}}]},
        "Use Cases": {"rich_text": [{"text": {"content": use_cases_string[:2000]}}]},
        "Status": {"select": {"name": "Active"}}
    }
    
    # 添加 URL
    if metadata.get("url"):
        properties["URL"] = {"url": metadata["url"]}
    
    # --- 核心修改：只傳遞 Category 和 Tags 的名稱 ---
    
    # 處理 Category
    category_obj = metadata.get("category")
    if category_obj and "name" in category_obj:
        # 只提取 'name' 來創建新的 select 物件
        properties["Category"] = {"select": {"name": category_obj["name"]}}
        
    # 處理 Tags
    tags_list = metadata.get("tags", [])
    if tags_list:
        # 遍歷列表，只提取每個 tag 的 'name'
        properties["Tags"] = {"multi_select": [{"name": tag["name"]} for tag in tags_list]}
        
    # ----------------------------------------------------
        
    return properties

def query_notion_database(token: str, database_id: str, filter_payload: dict, debug_mode: bool = False) -> list:
    """
    查詢 Notion 資料庫，並根據 debug_mode 決定是否打印詳細日誌。
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    results, has_more, start_cursor = [], True, None

    if debug_mode:
        print(f"🐞 [偵錯模式] 準備查詢 Notion 資料庫...")
        print(f"   - Database ID: {database_id}")
        print(f"   - Filter Payload: {json.dumps(filter_payload, indent=2)}")

    while has_more:
        payload = {"filter": filter_payload}
        if start_cursor: payload["start_cursor"] = start_cursor
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status() # 如果狀態碼不是 2xx，會在這裡拋出異常
            data = response.json()
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        except requests.exceptions.RequestException as e:
            # 這個 except 塊現在會捕獲 400 Bad Request 等錯誤
            print(f"❌ 查詢 Notion 資料庫時發生嚴重錯誤: {e}")
            try:
                # 嘗試解析錯誤詳情並打印
                error_details = response.json()
                print(f"   - Notion API 返回的錯誤詳情: {json.dumps(error_details, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                # 如果連錯誤詳情都無法解析，就打印原始文本
                print(f"   - Notion API 返回的原始錯誤文本: {response.text}")
            
            # 在偵錯模式下，提供更詳細的上下文
            if debug_mode:
                print("🐞 [偵錯模式] 檢查點:")
                print("   1. 請確認您的 `config.json` 中的 `NOTION_TOKEN` 和資料庫 ID 是否正確。")
                print("   2. 請確認您的 Integration (整合) 是否已分享給目標資料庫。")
                print("   3. 請仔細閱讀上面的『錯誤詳情』，它通常會明確指出哪個屬性名稱或類型有問題。")

            return [] # 返回空列表，表示查詢失敗

    print(f"✅ 成功從 Notion 查詢到 {len(results)} 筆資料。")
    return results

def update_notion_page_status(token: str, page_id: str, status: str):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
    properties = {"Status": {"select": {"name": status}}}
    payload = {"properties": properties}
    try:
        response = requests.patch(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print(f"✅ 成功更新頁面 {page_id} 狀態為 '{status}'")
    except requests.exceptions.RequestException as e:
        print(f"❌ 更新 Notion 頁面狀態時發生錯誤: {e}\n   錯誤詳情: {response.text}")

# --- 核心修改 1：讓 get_page_content_as_text 返回一個包含元數據的字典 ---
def get_page_content_as_text(page: dict) -> tuple[str, dict]:
    """
    從 Notion 頁面物件中提取關鍵文本內容和所有重要的元數據。
    返回: (文本內容, 元數據字典)
    """
    props = page.get("properties", {})
    
    # 提取文本內容
    title = props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "")
    short_summary = props.get("Short Summary", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
    extended_summary = props.get("Extended Summary", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
    content_string = f"Title: {title}\nShort Summary: {short_summary}\n\n{extended_summary}"
    
    # 提取元數據
    metadata = {
        "url": props.get("URL", {}).get("url"),
        "category": props.get("Category", {}).get("select"), # 獲取完整的 select 物件
        "tags": props.get("Tags", {}).get("multi_select", []) # 獲取完整的 multi_select 列表
    }
    
    return content_string, metadata
# --- 確保您有 _format_list_content 函式 ---
def _format_list_content(content) -> str:
    if isinstance(content, list):
        return "\n".join([f"• {item}" for item in content])
    elif isinstance(content, str):
        stripped_content = content.strip()
        if stripped_content.startswith('[') and stripped_content.endswith(']'):
            try:
                content_list = ast.literal_eval(stripped_content)
                if isinstance(content_list, list):
                    return "\n".join([f"• {item}" for item in content_list])
            except (ValueError, SyntaxError):
                pass
        return content
    return str(content)

def build_date_filter(period: str) -> dict:
    """根據期間（weekly, monthly, quarterly）建立 Notion API 的日期過濾器。"""
    today = date.today()
    if period == "weekly":
        # 為了確保能抓到本週的內容，我們從上週一開始算
        start_date = today - timedelta(days=today.weekday() + 7) 
    elif period == "monthly":
        # 從上個月第一天開始
        first_day_of_current_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        start_date = last_day_of_last_month.replace(day=1)
    elif period == "quarterly":
        # 從上個季度第一天開始
        current_quarter = (today.month - 1) // 3
        # 計算上個季度的起始月份 (1, 4, 7, 10)
        # 如果現在是Q1, 上個季度是去年Q4 (起始月份10)
        # 否則，是今年 (Q-1)*3+1
        if current_quarter == 0:
            start_month_of_last_quarter = 10
            year_of_last_quarter = today.year - 1
        else:
            start_month_of_last_quarter = (current_quarter - 1) * 3 + 1
            year_of_last_quarter = today.year
        start_date = date(year_of_last_quarter, start_month_of_last_quarter, 1)
    else: # 預設為過去 7 天
        start_date = today - timedelta(days=7)
        
    # --- 核心修改：使用正確的 "timestamp" 過濾器結構 ---
    return {
        "timestamp": "created_time",
        "created_time": {
            "on_or_after": start_date.isoformat()
        }
    }
    # ----------------------------------------------------

def format_review_properties(review_data: dict, period: str, start_date: date, end_date: date) -> dict:
    """將趨勢分析報告格式化為 Notion API 的屬性結構。"""
    
    # 將列表轉換為帶項目符號的字串
    trends_str = "\n".join([f"• {item}" for item in review_data.get("key_trends", [])])
    ideas_str = "\n".join([f"• {item}" for item in review_data.get("emerging_ideas", [])])
    actions_str = "\n".join([f"• {item}" for item in review_data.get("actionable_insights", [])])
    questions_str = "\n".join([f"• {item}" for item in review_data.get("unanswered_questions", [])])
    
    # 生成標題
    title = f"{period.capitalize()} Review: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Period": {"select": {"name": period.capitalize()}},
        "Date Range": {"date": {"start": start_date.isoformat(), "end": end_date.isoformat()}},
        "Overall Summary": {"rich_text": [{"text": {"content": review_data.get("overall_summary", "")}}]},
        "Key Trends": {"rich_text": [{"text": {"content": trends_str}}]},
        "Emerging Ideas": {"rich_text": [{"text": {"content": ideas_str}}]},
        "Actionable Insights": {"rich_text": [{"text": {"content": actions_str}}]},
        "Unanswered Questions": {"rich_text": [{"text": {"content": questions_str}}]}
    }
    return properties