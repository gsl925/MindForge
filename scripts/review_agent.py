# scripts/review_agent.py
import json
from .llm_handler import query_llm

def generate_periodic_review(consolidated_notes: str, period: str, config: dict) -> dict:
    """
    分析一段時間內的筆記合集，生成趨勢和洞見。
    """
    system_prompt = f"""
    你是一位頂尖的戰略分析師和研究員。你的任務是分析使用者在過去一段時間（{period}）內收集的筆記合集，從中提煉出高層次的洞見。

    **重要規則：**
    1.  你的所有輸出都必須使用「繁體中文」(Traditional Chinese)。
    2.  深入思考，不僅要總結，更要找出筆記之間的隱藏關聯、重複出現的主題和潛在的趨勢。
    3.  **特別注意**：筆記合集中，有些標題前會帶有 `[ORIGINAL IDEA]` 標記。這些是使用者的原創想法，具有極高的價值。你應該在分析時給予它們更高的權重，並在「新興想法 (emerging_ideas)」或「可執行洞見 (actionable_insights)」部分特別提及或基於它們進行發散思考。
    4.  你的輸出必須是單一、有效的 JSON 物件，不包含任何額外解釋。

    JSON 結構應包含以下鍵：
    - "overall_summary": (繁體中文) 對整個時期的學習和思考進行一個高度概括的執行摘要。
    - "key_trends": (繁體中文) 一個列表，列出 3-5 個在本時期內反覆出現或逐漸顯現的關鍵趨勢或主題。
    - "emerging_ideas": (繁體中文) 一個列表，列出一些獨立的、新穎的、值得關注的新想法或概念。**優先考慮從 `[ORIGINAL IDEA]` 標記的筆記中提煉。**
    - "actionable_insights": (繁體中文) 一個列表，根據觀察到的趨勢，提出 2-3 個具體的、可執行的建議或行動點。
    - "unanswered_questions": (繁體中文) 一個列表，提出一些由這些筆記引發的、值得未來進一步探索或研究的問題。
    """
    
    user_prompt = f"這是我的筆記合集，請進行分析：\n\n---\n{consolidated_notes}\n---"
    
    print("🧠 正在呼叫趨勢分析 Agent... (這將花費較長時間，請耐心等待)")
    response_content = query_llm(system_prompt, user_prompt, config, use_json_format=True)
    
    if response_content:
        try:
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            print(f"❌ 無法解析趨勢分析 Agent 的回應為 JSON: {e}")
            return None
    return None
