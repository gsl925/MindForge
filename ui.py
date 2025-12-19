# ui.py (最終完整版)

import streamlit as st
import os
import json
import time
import requests
from datetime import date

# --- 導入核心處理函式 ---
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
# --- UI 後端邏輯封裝 ---

def ui_process_and_save_content(raw_content: str, config: dict, url: str = None, source_type: str = None):
    """專為 UI 設計的 Inbox 處理函式"""
    if not raw_content or not raw_content.strip():
        st.warning("⚠️ 內容為空，已跳過處理。")
        return False
    processed_data = process_inbox_item(raw_content, config)
    if not processed_data:
        st.warning("⚠️ AI 智能處理失敗。不過別擔心，您的原始筆記仍會被保存。")
        processed_data = {}
        
    # 將 source_type 傳遞下去
    properties = format_inbox_properties(processed_data, raw_content, url, source_type=source_type)
    
    result = create_notion_page(config['NOTION_TOKEN'], config['INBOX_DB_ID'], properties)
    return result is not None

def ui_run_knowledge_synthesis(config: dict):
    """專為 UI 設計的知識合成函式"""
    st.info("🚀 開始知識合成...")
    filter_payload = {"property": "Status", "select": {"equals": "New"}}
    new_items = query_notion_database(config['NOTION_TOKEN'], config['INBOX_DB_ID'], filter_payload, config.get("DEBUG_MODE", False))
    if not new_items:
        st.success("✅ Inbox 中沒有需要合成的新項目。")
        return
    progress_bar = st.progress(0)
    total_items = len(new_items)
    st.info(f"找到 {total_items} 個新項目需要處理。")
    for i, item in enumerate(new_items):
        page_id = item['id']
        content_to_process, metadata = get_page_content_as_text(item)
        with st.expander(f"處理項目 {i+1}/{total_items}: {content_to_process[:80]}...", expanded=True):
            try:
                with st.spinner("🧠 正在呼叫 AI 生成知識節點..."):
                    knowledge_data = create_knowledge_node(content_to_process, config)
                if not knowledge_data:
                    st.error("❌ AI 未能生成有效的知識節點。已跳過。")
                    continue
                with st.spinner("✍️ 正在寫入 Notion..."):
                    # --- 核心修改：傳遞 metadata 字典 ---
                    properties = format_knowledge_properties(knowledge_data, metadata=metadata)
                    # ------------------------------------
                    result = create_notion_page(config['NOTION_TOKEN'], config['KNOWLEDGE_DB_ID'], properties)
                if result:
                    st.success(f"✅ 項目 '{knowledge_data.get('title', 'Untitled')}' 已成功合成！")
                    update_notion_page_status(config['NOTION_TOKEN'], page_id, "Processed")
                    # --- 新增：發送 Email ---
                    with st.spinner("📧 正在準備並發送 Email..."):
                        email_subject, email_body = format_knowledge_node_as_html(knowledge_data, metadata)
                        # 注意：Streamlit 無法處理 getpass，所以這裡會直接在終端機提示
                        send_email(f"New Knowledge Node: {email_subject}", email_body, config)
                    # ------------------------                    
                else:
                    st.error("❌ 寫入 Notion 失敗！請檢查終端機。")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ 與 AI 服務的連接超時或失敗！")
                st.warning("這很可能是本地 Ollama 服務崩潰。")
                st.stop()
            except Exception as e:
                st.error(f"❌ 處理過程中發生未知錯誤: {e}")
                continue
        progress_bar.progress((i + 1) / total_items)
        if i < total_items - 1:
            delay = 5
            st.info(f"🔄 等待 {delay} 秒以釋放資源...")
            time.sleep(delay)
    st.success("✅ 知識合成流程全部完成！")

def ui_run_review(period: str, config: dict):
    """專為 UI 設計的趨勢分析函式"""
    with st.spinner(f"🔍 正在從 Notion 抓取 {period} 筆記..."):
        date_filter = build_date_filter(period)
        notes = query_notion_database(config['NOTION_TOKEN'], config['KNOWLEDGE_DB_ID'], date_filter, config.get("DEBUG_MODE", False))
    if not notes:
        st.success(f"✅ 在指定期間内沒有找到新的知識節點。")
        return
    st.info(f"找到 {len(notes)} 篇筆記，正在進行濃縮...")
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
    with st.expander("顯示用於分析的濃縮文本"):
        st.markdown(consolidated_text)
    review_data = generate_periodic_review(consolidated_text, period, config)
    if not review_data:
        st.error("❌ 趨勢分析失敗，已終止。")
        return
    with st.spinner("✍️ 正在將趨勢報告寫入 Notion..."):
        start_date = date.fromisoformat(date_filter['created_time']['on_or_after'])
        end_date = date.today()
        review_properties = format_review_properties(review_data, period, start_date, end_date)
        result = create_notion_page(config['NOTION_TOKEN'], config['REVIEW_DB_ID'], review_properties)
    if result:
        st.success(f"✅ {period.capitalize()} 趨勢分析報告已成功生成！")
        # --- 新增：發送 Email ---
        with st.spinner("📧 正在準備並發送 Email..."):
            email_subject, email_body = format_review_as_html(review_data, period)
            # 注意：Streamlit 無法處理 getpass，所以這裡會直接在終端機提示
            send_email(email_subject, email_body, config)
        # ------------------------        
    else:
        st.error(f"❌ 趨勢分析報告儲存失敗。請檢查終端機的詳細錯誤訊息。")

# --- Streamlit UI 主體 ---

st.set_page_config(page_title="JimLocalBrain", layout="wide")
st.title("🧠 JimLocalBrain - 您的本地 AI 外腦系統")

@st.cache_resource
def load_config_and_init():
    """載入設定並根據模式執行初始化"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        st.error(f"❌ 載入設定檔 config.json 失敗: {e}")
        st.stop()
        return None
    provider = config.get("LLM_PROVIDER", "local")
    if provider == "local":
        local_api_url = config.get("LOCAL_CONFIG", {}).get("LLM_API_BASE_URL", "http://localhost:11434")
        with st.spinner("🩺 正在檢查本地 Ollama 服務狀態..."):
            if not check_and_start_ollama(local_api_url):
                st.error("❌ 無法啟動或連接到本地 Ollama 服務。請手動檢查。")
                st.stop()
    return config

# --- 1. 執行設定載入 ---
CONFIG = load_config_and_init()
if not CONFIG:
    st.stop()

# --- 2. 顯示 UI 元件 (現在可以安全地使用 CONFIG) ---
provider_display = {"local": "💻 本地模式 (Local)", "cloud": "☁️ 雲端模式 (Cloud)"}.get(CONFIG.get("LLM_PROVIDER"), "未知")
st.info(f"當前運行模式: **{provider_display}**")

st.header("📥 快速新增至 Inbox")
tab1, tab2, tab3 = st.tabs(["✍️ 新增文字/靈感", "🔗 新增網址", "🖼️ 新增圖片 (OCR)"])
spinner_text = f"🤖 正在使用 {CONFIG.get('LLM_PROVIDER')} AI 處理..."
with tab1:
    text_input = st.text_area("內容:", height=200, placeholder="在這裡貼上您的文章、筆記、會議記錄或一閃而過的靈感...")
    if st.button("新增文字", key="add_text"):
        if text_input:
            with st.spinner(spinner_text):
                if ui_process_and_save_content(text_input, CONFIG, source_type='text'):
                    st.success("✅ 成功新增至 Notion Inbox！")
        else:
            st.warning("請輸入內容。")
with tab2:
    url_input = st.text_input("URL:", placeholder="https://example.com/article")
    if st.button("新增網址", key="add_url"):
        if url_input:
            with st.spinner("🕸️ 正在抓取網頁..."):
                content = get_content_from_url(url_input)
            if content:
                with st.spinner(spinner_text):
                    if ui_process_and_save_content(content, CONFIG, url=url_input, source_type='url'):
                        st.success("✅ 成功從網址新增至 Notion Inbox！")
            else:
                st.error("❌ 無法從該網址抓取內容。")
        else:
            st.warning("請輸入 URL。")
with tab3:
    uploaded_file = st.file_uploader("選擇一張圖片 (截圖、文件照片...)", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        if st.button("新增圖片", key="add_img"):
            temp_path = os.path.join("data", "temp_image.png")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("🖼️ 正在進行 OCR..."):
                content = get_text_from_image(temp_path)
            if content:
                with st.spinner(spinner_text):
                    if ui_process_and_save_content(content, CONFIG, source_type='image'):
                        st.success("✅ 成功從圖片新增至 Notion Inbox！")
            else:
                st.error("❌ 無法從圖片中提取文字。")
            os.remove(temp_path)

st.header("⚙️ 批次處理與同步")
st.subheader("知識合成")
st.info("將 Notion Inbox 中『New』狀態的項目，轉換為知識節點。")
if st.button("執行知識合成"):
    ui_run_knowledge_synthesis(CONFIG)

st.header("📊 趨勢分析與回顧")
period_option = st.selectbox("選擇您想回顧的期間：", ("weekly", "monthly", "quarterly"), format_func=lambda x: x.capitalize())
if st.button(f"生成 {period_option.capitalize()} 趨勢報告"):
    ui_run_review(period_option, CONFIG)
