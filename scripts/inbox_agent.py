import json
from newspaper import Article, Config
from PIL import Image
import pytesseract
from .llm_handler import query_llm # 導入新的 query_llm

# 修改函式簽名
def process_inbox_item(raw_content: str, config: dict) -> dict:
    """
    使用 LLM 處理單一原始輸入，並回傳結構化 JSON。
    """
    system_prompt = """
    你是一個高效的資訊處理助理。你的任務是分析使用者提供的文本，並嚴格按照指定的 JSON 格式輸出結果。
    **重要規則：你的所有輸出，包括標題、摘要和標籤，都必須使用「繁體中文」(Traditional Chinese) 來書寫，絕對不允許出現任何簡體字。**
    你的輸出必須是一個單一、有效的 JSON 物件，不包含任何額外的解釋或 markdown 標記。
    **確保所有指定的鍵都存在於 JSON 輸出中，特別是 "title"，它絕對不能被省略。**

    JSON 結構應包含以下鍵：
    - "title": (必要欄位) 為文本生成一個簡潔、精確的標題。
    - "short_summary"(繁體中文): 生成一個不超過 5 句話的核心摘要。
    - "extended_summary"(繁體中文): 生成一個更詳細的摘要，約 2-3 段。
    - "category": 從以下選項中選擇最合適的一個分類：'Knowledge', 'Tool Idea', 'Process', 'Insight', 'Book Note', 'Meeting Note'。
    - "tags": 生成 3 到 5 個相關的關鍵字標籤，以陣列形式提供。
    """
    user_prompt = f"請處理以下文本：\n\n---\n{raw_content}\n---"
    print("🧠 正在呼叫 Inbox Agent 處理內容...")
    # 使用新的 query_llm 函式
    response_content = query_llm(system_prompt, user_prompt, config)
    if response_content:
        try:
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            print(f"❌ 無法解析 LLM 回應為 JSON: {e}\n   收到的原始回應: {response_content}")
            return None
    return None

def get_content_from_url(url: str) -> str:
    """
    從 URL 抓取主要文章內容，並偽裝成瀏覽器以避免 403 錯誤。
    """
    try:
        print(f"🕸️ 正在從 URL 抓取內容: {url}")
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        config.request_timeout = 15
        article = Article(url, config=config)
        article.download()
        article.parse()
        return f"Title: {article.title}\n\n{article.text}"
    except Exception as e:
        print(f"❌ 從 URL 抓取內容失敗: {e}")
        return None

def get_text_from_image(image_path: str) -> str:
    """從圖片路徑使用 OCR 提取文字。"""
    try:
        print(f"🖼️ 正在從圖片進行 OCR: {image_path}")
        text = pytesseract.image_to_string(Image.open(image_path), lang='eng+chi_tra')
        return text
    except FileNotFoundError:
        print(f"❌ 找不到圖片檔案: {image_path}")
        return None
    except Exception as e:
        print(f"❌ OCR 處理失敗: {e}")
        return None
