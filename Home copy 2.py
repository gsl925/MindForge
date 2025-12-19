# Home.py (修正版，解決執行緒間 session_state 的問題)

import streamlit as st
import os
import json
import time
import requests
from datetime import date
import threading

# --- 導入核心處理函式 (不變) ---
from scripts.health_check import check_and_start_ollama
from scripts.inbox_agent import get_content_from_url, get_text_from_image, process_inbox_item
from scripts.knowledge_agent import create_knowledge_node
from scripts.review_agent import generate_periodic_review
from scripts.notion_handler import (
    create_notion_page, format_inbox_properties, format_knowledge_properties,
    query_notion_database, update_notion_page_status, get_page_content_as_text,
    build_date_filter, format_review_properties
)
from scripts.email_handler import send_email, format_knowledge_node_as_html, format_review_as_html

# --- 背景任務函式 ---

# --- 核心修改 1: 背景函式現在接收一個 status_dict 作為參數 ---
def background_add_to_inbox(config: dict, status_dict: dict, task_type: str, content: str, url: str = None):
    """通用於新增到 Inbox 的背景任務。"""
    try:
        status_dict["running"] = True
        status_dict["message"] = "正在處理..."
        
        raw_content = ""
        source_type = task_type
        
        if task_type == 'text':
            raw_content = content
            status_dict["message"] = "🤖 正在呼叫 AI 處理文本..."
        elif task_type == 'url':
            status_dict["message"] = "🕸️ 正在抓取網頁內容..."
            raw_content = get_content_from_url(content)
            url = content
        elif task_type == 'image':
            status_dict["message"] = "🖼️ 正在進行 OCR 識別..."
            raw_content = get_text_from_image(content)
            os.remove(content)

        if not raw_content or not raw_content.strip():
            status_dict["error"] = f"❌ 無法獲取內容 ({task_type})。"
            return

        status_dict["message"] = "🤖 正在進行智能摘要..."
        processed_data = process_inbox_item(raw_content, config)
        if not processed_data:
            status_dict["logs"].append("⚠️ AI 智能處理失敗，但原始筆記仍會保存。")
            processed_data = {}

        status_dict["message"] = "✍️ 正在寫入 Notion..."
        properties = format_inbox_properties(processed_data, raw_content, url, source_type=source_type)
        result = create_notion_page(config['NOTION_TOKEN'], config['INBOX_DB_ID'], properties, page_content=raw_content)

        if result:
            status_dict["success"] = "✅ 成功新增至 Notion Inbox！"
        else:
            status_dict["error"] = "❌ 新增至 Notion Inbox 失敗。"

    except Exception as e:
        status_dict["error"] = f"❌ 處理過程中發生錯誤: {e}"
    finally:
        status_dict["running"] = False

def background_knowledge_synthesis(config: dict, status_dict: dict):
    """知識合成的背景任務。"""
    try:
        # --- 核心修改 1: 在 status_dict 中初始化一個成功標記 ---
        status_dict["synthesis_happened"] = False
                
        status_dict["logs"].append("正在查詢需要處理的新項目...")
        filter_payload = {"property": "Status", "select": {"equals": "New"}}
        new_items = query_notion_database(config['NOTION_TOKEN'], config['INBOX_DB_ID'], filter_payload, config.get("DEBUG_MODE", False))
        
        if not new_items:
            status_dict["logs"].append("✅ Inbox 中沒有需要合成的新項目。")
            return

        total_items = len(new_items)
        status_dict["total"] = total_items
        status_dict["logs"].append(f"找到 {total_items} 個新項目需要處理。")

        synthesis_successful = False
        for i, item in enumerate(new_items):
            page_id = item['id']
            status_dict["current_task"] = f"正在處理項目 {i+1}/{total_items}..."
            content_to_process, metadata = get_page_content_as_text(config['NOTION_TOKEN'], item)
            
            if not content_to_process.strip():
                status_dict["logs"].append(f"⚠️ 項目 {page_id} 內容為空，已跳過。")
                continue

            try:
                status_dict["logs"].append(f"🧠 項目 '{content_to_process[:30]}...': 正在呼叫 AI...")
                knowledge_data = create_knowledge_node(content_to_process, config)
                if not knowledge_data:
                    status_dict["logs"].append(f"❌ AI 未能生成有效節點。")
                    continue

                status_dict["logs"].append(f"✍️ 正在寫入 Notion: '{knowledge_data.get('title', 'Untitled')}'")
                properties = format_knowledge_properties(knowledge_data, metadata=metadata)
                result = create_notion_page(config['NOTION_TOKEN'], config['KNOWLEDGE_DB_ID'], properties)
                
                if result:
                    status_dict["logs"].append(f"✅ 合成成功！")
                    update_notion_page_status(config['NOTION_TOKEN'], page_id, "Processed")
                    # --- 核心修改 2: 更新 status_dict 中的標記，而不是 session_state ---
                    status_dict["synthesis_happened"] = True
                else:
                    status_dict["logs"].append(f"❌ 寫入 Notion 失敗！")
            except Exception as e:
                status_dict["logs"].append(f"❌ 處理項目時發生錯誤: {e}")
            
            status_dict["progress"] = i + 1
            if i < total_items - 1:
                status_dict["logs"].append("🔄 等待 5 秒...")
                time.sleep(5)

        # --- 核心修改 3: 移除舊的、錯誤的 session_state 寫入 ---
        # if synthesis_successful:
        #     st.session_state.data_updated = True # <--- 刪除這一整塊
        status_dict["current_task"] = "✅ 知識合成流程全部完成！"
    except Exception as e:
        status_dict["current_task"] = f"❌ 背景任務發生嚴重錯誤: {e}"
    finally:
        status_dict["running"] = False

def background_run_review(config: dict, status_dict: dict, period: str):
    """趨勢分析的背景任務。"""
    try:
        status_dict["running"] = True
        status_dict["message"] = f"🔍 正在從 Notion 抓取 {period} 筆記..."
        date_filter = build_date_filter(period)
        notes = query_notion_database(config['NOTION_TOKEN'], config['KNOWLEDGE_DB_ID'], date_filter, config.get("DEBUG_MODE", False))
        
        if not notes:
            status_dict["success"] = f"✅ 在指定期間内沒有找到新的知識節點。"
            return

        status_dict["message"] = f"找到 {len(notes)} 篇筆記，正在進行濃縮..."
        consolidated_notes = [f"## {note['properties']['Title']['title'][0]['text']['content']}\n> {note['properties']['Core Idea']['rich_text'][0]['text']['content']}\n" for note in notes]
        consolidated_text = "\n---\n".join(consolidated_notes)
        
        status_dict["message"] = f"🤖 正在呼叫 AI 生成 {period} 趨勢報告..."
        review_data = generate_periodic_review(consolidated_text, period, config)
        if not review_data:
            status_dict["error"] = "❌ 趨勢分析失敗，AI 未返回有效數據。"
            return

        status_dict["message"] = "✍️ 正在將趨勢報告寫入 Notion..."
        start_date = date.fromisoformat(date_filter['created_time']['on_or_after'])
        end_date = date.today()
        review_properties = format_review_properties(review_data, period, start_date, end_date)
        result = create_notion_page(config['NOTION_TOKEN'], config['REVIEW_DB_ID'], review_properties)
        
        if result:
            status_dict["success"] = f"✅ {period.capitalize()} 趨勢分析報告已成功生成！"
        else:
            status_dict["error"] = f"❌ 趨勢分析報告儲存失敗。"
            
    except Exception as e:
        status_dict["error"] = f"❌ 趨勢分析過程中發生錯誤: {e}"
    finally:
        status_dict["running"] = False

# --- Streamlit UI 主體 ---
st.set_page_config(page_title="MindForge", page_icon="🏠", layout="wide")

# --- 核心修改 2: 使用一個統一的字典來儲存所有狀態 ---
if 'tasks_status' not in st.session_state:
    st.session_state.tasks_status = {
        "synthesis": {"running": False, "progress": 0, "total": 0, "current_task": "", "logs": []},
        "inbox": {"running": False, "message": "", "success": "", "error": "", "logs": []},
        "review": {"running": False, "message": "", "success": "", "error": ""}
    }
if 'data_updated' not in st.session_state:
    st.session_state.data_updated = False

# 頁面標題和介紹 (不變)
st.title("🧠 MindForge - Your Cognition Forge")
st.markdown("Welcome! Use the tools below to capture and process information. Navigate to the **Dashboard** page in the sidebar to analyze your knowledge base.")
st.markdown("---")

# 載入設定檔並初始化 (不變)
@st.cache_resource
def load_config_and_init():
    # ... (此函式內容完全不變)
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        st.error(f"❌ 載入設定檔 config.json 失敗: {e}")
        st.stop()
    provider = config.get("LLM_PROVIDER", "local")
    if provider == "local":
        local_api_url = config.get("LOCAL_CONFIG", {}).get("LLM_API_BASE_URL", "http://localhost:11434")
        with st.spinner("🩺 正在檢查本地 Ollama 服務狀態..."):
            if not check_and_start_ollama(local_api_url):
                st.error("❌ 無法啟動或連接到本地 Ollama 服務。請手動檢查。")
                st.stop()
    return config

CONFIG = load_config_and_init()
if not CONFIG:
    st.stop()

provider_display = {"local": "💻 本地模式 (Local)", "cloud": "☁️ 雲端模式 (Cloud)"}.get(CONFIG.get("LLM_PROVIDER"), "未知")
st.info(f"當前運行模式: **{provider_display}**")

# --- 1. Quick Add to Inbox ---
st.header("📥 Quick Add to Inbox")

# --- 核心修改 3: 從新的 tasks_status 結構中讀取狀態 ---
inbox_status = st.session_state.tasks_status["inbox"]
if inbox_status["running"]:
    st.info(f"⏳ {inbox_status['message']}")
elif inbox_status["success"]:
    st.success(inbox_status["success"])
    inbox_status["success"] = ""
elif inbox_status["error"]:
    st.error(inbox_status["error"])
    inbox_status["error"] = ""

tab1, tab2, tab3 = st.tabs(["✍️ Add Text/Idea", "🔗 Add URL", "🖼️ Add Image (OCR)"])
is_task_running = any(st.session_state.tasks_status[task]["running"] for task in st.session_state.tasks_status)

with tab1:
    text_input = st.text_area("Content:", height=200, placeholder="Paste your articles, notes, meeting minutes, or fleeting ideas here...")
    if st.button("Add Text", key="add_text", disabled=is_task_running):
        if text_input:
            # --- 核心修改 4: 重置狀態字典並將其作為參數傳遞 ---
            st.session_state.tasks_status["inbox"] = {"running": True, "message": "正在初始化...", "success": "", "error": "", "logs": []}
            threading.Thread(target=background_add_to_inbox, args=(CONFIG, st.session_state.tasks_status["inbox"], 'text', text_input), daemon=True).start()
            st.rerun()
        else:
            st.warning("Please enter some content.")

with tab2:
    url_input = st.text_input("URL:", placeholder="https://example.com/article")
    if st.button("Add URL", key="add_url", disabled=is_task_running):
        if url_input:
            st.session_state.tasks_status["inbox"] = {"running": True, "message": "正在初始化...", "success": "", "error": "", "logs": []}
            threading.Thread(target=background_add_to_inbox, args=(CONFIG, st.session_state.tasks_status["inbox"], 'url', url_input), daemon=True).start()
            st.rerun()
        else:
            st.warning("Please enter a URL.")

with tab3:
    uploaded_file = st.file_uploader("Choose an image (screenshot, document photo...)", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        if st.button("Add Image", key="add_img", disabled=is_task_running):
            if not os.path.exists("data"): os.makedirs("data")
            temp_path = os.path.join("data", "temp_image.png")
            with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
            st.session_state.tasks_status["inbox"] = {"running": True, "message": "正在初始化...", "success": "", "error": "", "logs": []}
            threading.Thread(target=background_add_to_inbox, args=(CONFIG, st.session_state.tasks_status["inbox"], 'image', temp_path), daemon=True).start()
            st.rerun()

# --- 2. Knowledge Synthesis ---
st.header("⚙️ Batch Processing & Synthesis")
st.subheader("Knowledge Synthesis")
st.markdown("Process items from your Notion Inbox with `New` status and convert them into structured knowledge nodes.")

synthesis_status = st.session_state.tasks_status["synthesis"]
if st.button("Run Knowledge Synthesis", disabled=is_task_running):
    st.session_state.tasks_status["synthesis"] = {"running": True, "progress": 0, "total": 0, "current_task": "正在初始化...", "logs": []}
    threading.Thread(target=background_knowledge_synthesis, args=(CONFIG, st.session_state.tasks_status["synthesis"]), daemon=True).start()
    st.rerun()

if synthesis_status["running"]:
    progress_value = synthesis_status["progress"] / synthesis_status["total"] if synthesis_status["total"] > 0 else 0
    st.progress(progress_value, text=f"進度: {synthesis_status['progress']}/{synthesis_status['total']} - {synthesis_status['current_task']}")
    with st.expander("顯示詳細日誌", expanded=True):
        log_container = st.container(height=300)
        for log in reversed(synthesis_status["logs"]):
            log_container.write(log)
    time.sleep(2)
    st.rerun()
elif synthesis_status["logs"]:
    # --- 核心修改 4: 在任務結束後，檢查成功標記並更新 session_state ---
    # 這個區塊只在任務從 running -> not running 時執行一次
    if synthesis_status.get("synthesis_happened", False):
        st.session_state.data_updated = True
        st.toast("✅ 合成完成！儀表板數據將在下次訪問時更新。")
        # 重置標記，避免不必要的重複觸發
        synthesis_status["synthesis_happened"] = False
        
    st.info("上次合成任務已結束。")
    with st.expander("顯示上次運行的詳細日誌"):
        log_container = st.container(height=300)
        for log in reversed(synthesis_status["logs"]):
            log_container.write(log)

# --- 3. Trend Analysis & Review ---
st.header("📊 Trend Analysis & Review")

review_status = st.session_state.tasks_status["review"]
if review_status["running"]:
    st.info(f"⏳ {review_status['message']}")
elif review_status["success"]:
    st.success(review_status["success"])
    review_status["success"] = ""
elif review_status["error"]:
    st.error(review_status["error"])
    review_status["error"] = ""

period_option = st.selectbox("Select the period you want to review:", ("weekly", "monthly", "quarterly"), format_func=lambda x: x.capitalize())
if st.button(f"Generate {period_option.capitalize()} Trend Report", disabled=is_task_running):
    st.session_state.tasks_status["review"] = {"running": True, "message": "正在初始化...", "success": "", "error": ""}
    threading.Thread(target=background_run_review, args=(CONFIG, st.session_state.tasks_status["review"], period_option), daemon=True).start()
    st.rerun()

