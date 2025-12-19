# pages/1_📊_Dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
from datetime import datetime
import tzlocal  # <--- 導入新的套件

# 導入我們自己的函式
# Streamlit 的多頁面應用會自動處理路徑問題
from scripts.notion_handler import query_notion_database

# --- 數據加載與處理 ---

@st.cache_data(ttl=600) # 快取數據 10 分鐘，避免頻繁請求 Notion
def load_knowledge_data(config):
    """從 Notion 加載所有知識節點並轉換為 Pandas DataFrame。"""
    print("Fetching data from Notion...")
    all_pages = query_notion_database(config['NOTION_TOKEN'], config['KNOWLEDGE_DB_ID'], filter_payload={}, debug_mode=config.get("DEBUG_MODE", False))
    
    if not all_pages:
        return pd.DataFrame()

    parsed_data = []
    for page in all_pages:
        props = page.get("properties", {})
        title_prop = props.get("Title", {}).get("title", [{}])
        title = title_prop[0].get("text", {}).get("content", "") if title_prop else "Untitled"
        
        category_prop = props.get("Category", {}).get("select", {})
        category = category_prop.get("name") if category_prop else "Uncategorized"
        
        tags_prop = props.get("Tags", {}).get("multi_select", [])
        tags = [tag.get("name") for tag in tags_prop]
        
        created_time = page.get("created_time")
        
        parsed_data.append({
            "title": title,
            "is_original": "💡" in title,
            "category": category,
            "tags": tags,
            "created_time": created_time
        })
        
    df = pd.DataFrame(parsed_data)
    # 將時間字串轉換為可操作的 datetime 物件
    df['created_time'] = pd.to_datetime(df['created_time'])
    return df

# --- 主應用程式 ---

st.set_page_config(page_title="MindForge Dashboard", layout="wide")
st.title("📊 Knowledge Base Dashboard")

# --- 核心修改：檢查 session_state 並在需要時清除快取 ---
if 'data_updated' not in st.session_state:
    st.session_state.data_updated = False

if st.session_state.data_updated:
    st.toast("🔄 數據已更新，正在重新加載儀表板...")
    st.cache_data.clear()  # 清除所有 @st.cache_data 的快取
    st.session_state.data_updated = False # 重置標記，避免不必要的重複刷新
# ----------------------------------------------------

# 加載設定檔
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    st.error("❌ 找不到設定檔 `config.json`。請確保主應用程式目錄中有此檔案。")
    st.stop()

df = load_knowledge_data(CONFIG)

if df.empty:
    st.warning("您的知識庫中還沒有任何數據！")
    st.stop()

# --- 側邊欄篩選器 ---
st.sidebar.header("Filters")

# 1. 時間範圍篩選器
min_date = df['created_time'].min().date()
max_date = df['created_time'].max().date()
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 2. 分類篩選器
all_categories = df['category'].unique()
selected_categories = st.sidebar.multiselect(
    "Select Categories",
    options=all_categories,
    default=all_categories
)

# --- 應用篩選器 ---
# 將從 date_input 得到的 date 物件轉換為 pandas 的 Timestamp，並立即賦予 UTC 時區
start_date_filter = pd.to_datetime(date_range[0]).tz_localize('UTC')

# 對於結束日期，我們先把它設置為當天的最後一秒，然後再賦予 UTC 時區
end_date_filter = pd.to_datetime(date_range[1]).replace(hour=23, minute=59, second=59).tz_localize('UTC')

filtered_df = df[
    (df['created_time'] >= start_date_filter) &
    (df['created_time'] <= end_date_filter) &
    (df['category'].isin(selected_categories))
]

if filtered_df.empty:
    st.warning("在選定的篩選條件下沒有找到任何數據。")
    st.stop()

# --- 核心指標 (KPIs) ---
total_nodes = len(filtered_df)
original_ideas = filtered_df['is_original'].sum()
num_categories = filtered_df['category'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("Total Knowledge Nodes", total_nodes)
col2.metric("💡 Original Ideas", original_ideas)
col3.metric("Unique Categories", num_categories)

st.markdown("---")

# --- 視覺化圖表 ---
col1, col2 = st.columns(2)

with col1:
    # 1. 分類圓餅圖
    st.subheader("Category Distribution")
    category_counts = filtered_df['category'].value_counts()
    fig_pie = px.pie(
        category_counts, 
        values=category_counts.values, 
        names=category_counts.index,
        title="Knowledge Nodes by Category"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # 3. 標籤詞雲
    st.subheader("Popular Tags")
    all_tags = [tag for tags_list in filtered_df['tags'] for tag in tags_list]
    if all_tags:
        text = " ".join(all_tags)
        
        # --- 核心修改：指定中文字體路徑 ---
        # 根據您的作業系統選擇合適的路徑
        # 對於 Windows:
        font_path = "fonts/NotoSansTC-Regular.ttf"
        # 對於 macOS:
        # font_path = "/System/Library/Fonts/PingFang.ttc" 
        
        try:
            wordcloud = WordCloud(
                width=800, 
                height=400, 
                background_color='white',
                font_path=font_path  # <--- 在這裡指定字體
            ).generate(text)
            
            fig_wc, ax = plt.subplots()
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig_wc)
            
        except FileNotFoundError:
            st.error(f"字體檔案未找到: {font_path}")
            st.warning("詞雲無法顯示中文字元。請檢查您的系統中是否存在該字體，或修改程式碼中的 `font_path`。")
        except Exception as e:
            st.error(f"生成詞雲時發生錯誤: {e}")

    else:
        st.info("No tags found in the selected data.")

with col2:
    # 2. 趨勢柱狀圖 (按月)
    st.subheader("Nodes Added Over Time")
    nodes_per_month = filtered_df.set_index('created_time').resample('M').size().reset_index(name='count')
    nodes_per_month['created_time'] = nodes_per_month['created_time'].dt.strftime('%Y-%m')
    fig_bar = px.bar(
        nodes_per_month, 
        x='created_time', 
        y='count',
        title="Monthly Knowledge Creation Trend",
        labels={'created_time': 'Month', 'count': 'Number of Nodes'}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# --- 原始數據表格 ---
st.subheader("Filtered Data")

# 複製一份 DataFrame 以免影響原始數據
display_df = filtered_df.copy()

# --- 核心修改：動態獲取本地時區並進行轉換 ---
try:
    # 1. 自動偵測本地時區名稱 (例如 'Asia/Taipei')
    local_tz_name = tzlocal.get_localzone_name()
    st.info(f"偵測到本地時區: {local_tz_name}，正在進行時間轉換...")

    # 2. 將 'created_time' 欄位從 UTC 轉換到偵測到的本地時區
    display_df['created_time'] = display_df['created_time'].dt.tz_convert(local_tz_name)

except Exception as e:
    st.warning(f"自動時區轉換失敗: {e}")
    st.info("將繼續顯示 UTC 時間。您可以嘗試手動在程式碼中指定時區，例如 'Asia/Taipei'。")

# 為了更好的可讀性，格式化時間字串 (並移除時區資訊)
# 我們可以在格式化之前，先用 tz_localize(None) 移除時區資訊，讓 strftime 更乾淨
display_df['created_time'] = display_df['created_time'].dt.tz_localize(None).dt.strftime('%Y-%m-%d %H:%M:%S')

# 顯示處理過的 DataFrame
st.dataframe(display_df)
