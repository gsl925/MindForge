import json
from .llm_handler import query_llm # 導入新的 query_llm

# 修改函式簽名
def create_knowledge_node(content: str, config: dict) -> dict:
    system_prompt = """
    你是一位知識整合專家。你的任務是將輸入的筆記和摘要，提煉成一個結構化的知識節點。
     **重要規則：你的所有輸出，包括標題、摘要和標籤，都必須使用「繁體中文」(Traditional Chinese) 來書寫，絕對不允許出現任何簡體字。**
    請嚴格按照指定的 JSON 格式輸出結果，不要包含任何額外說明。

    JSON 結構應包含以下鍵：
    - "title": 為這個知識節點生成一個精確的標題。
    - "core_idea"(繁體中文): 用一兩句話總結最核心的概念。
    - "notes"(繁體中文): 將原始內容整理成有條理的筆記（可使用條列式）。
    - "key_insights"(繁體中文): 提煉出 2-4 個關鍵的洞見或啟發。
    - "use_cases"(繁體中文): 思考並列出該知識的潛在應用場景。
    """
    user_prompt = f"請將以下內容轉換為知識節點：\n\n---\n{content}\n---"
    # ---------------------------
    
    print("🧠 正在呼叫 Knowledge Agent 生成知識節點...")
    # 使用新的 query_llm 函式
    response_content = query_llm(system_prompt, user_prompt, config, use_json_format=True)
    if response_content:
        try:
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            print(f"❌ 無法解析 LLM 回應為 JSON: {e}")
            return None
    return None

def generate_insight_report(items: list, api_url: str, model: str) -> str:
    system_prompt = """
    你是一位戰略分析師。你的任務是綜合分析使用者提供的一系列知識點，並生成一份富有洞見的週報。
    報告應包含以下部分：
    1.  **本週新知總結**: 總結這些新知識的核心主題。
    2.  **潛在連結**: 思考這些新知識之間，或與過去可能存在的知識之間有何關聯。
    3.  **新工具/流程想法**: 基於這些洞見，提出 1-3 個具體的工具開發想法或流程改進建議。
    4.  **行動項目**: 列出 2-3 個可以立即執行的具體行動步驟。
    
    請以清晰的 Markdown 格式輸出報告。
    """
    formatted_items = "\n\n".join([f"--- 項目 {i+1} ---\n{item}" for i, item in enumerate(items)])
    user_prompt = f"請基於以下知識點生成一份洞見報告：\n\n{formatted_items}"
    print("🧠 正在呼叫 Knowledge Agent 生成洞見報告...")
    # 報告不需要 JSON 格式
    report_content = query_local_llm(system_prompt, user_prompt, api_url, model, use_json_format=False)
    return report_content if report_content else "無法生成報告。"
