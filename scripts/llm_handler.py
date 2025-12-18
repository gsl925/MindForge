# scripts/llm_handler.py (支援本地與雲端雙模式)
import requests
import json
import re

def query_llm(system_prompt: str, user_prompt: str, config: dict, use_json_format: bool = True) -> str:
    """
    根據設定，向本地或雲端 Ollama 服務發送請求。
    """
    provider = config.get("LLM_PROVIDER", "local")
    debug_mode = config.get("DEBUG_MODE", False) # 讀取偵錯模式開關

    if provider == "cloud":
        print("☁️ 正在使用 Ollama Cloud...")
        # 雲端模式通常比較穩定，暫不為其添加複雜的偵錯日誌
        return query_ollama_cloud(system_prompt, user_prompt, config.get("CLOUD_CONFIG", {}), use_json_format)
    else:
        # 將 debug_mode 傳遞給本地處理函式
        return query_ollama_local(system_prompt, user_prompt, config.get("LOCAL_CONFIG", {}), use_json_format, debug_mode)

def query_ollama_cloud(system_prompt: str, user_prompt: str, cloud_config: dict, use_json_format: bool):
    """處理對 Ollama Cloud API 的呼叫 (使用新版 /v1 API)。"""
    api_key = cloud_config.get("OLLAMA_API_KEY")
    model = cloud_config.get("LLM_MODEL_NAME")
    api_url = "https://ollama.com/v1/chat/completions"

    if not api_key or "YOUR_OLLAMA_CLOUD_API_KEY" in api_key:
        print("❌ 錯誤：Ollama Cloud API 金鑰未設定。請在 config.json 中填寫。")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    if use_json_format:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=600)
        response.raise_for_status()
        response_data = response.json()
        content = response_data['choices'][0]['message']['content']
        return content
    except requests.exceptions.RequestException as e:
        print(f"❌ 與 Ollama Cloud 連接時發生錯誤: {e}\n   錯誤詳情: {response.text}")
        return None
    except (KeyError, IndexError) as e:
        print(f"❌ 解析 Ollama Cloud 回應時發生錯誤: {e}\n   收到的原始回應: {response.text}")
        return None

def query_ollama_local(system_prompt: str, user_prompt: str, local_config: dict, use_json_format: bool, debug_mode: bool = False):
    """處理對本地 Ollama 的呼叫，並根據 debug_mode 決定是否打印詳細日誌。"""
    api_url = local_config.get("LLM_API_BASE_URL")
    model = local_config.get("LLM_MODEL_NAME")
    generate_url = f"{api_url}/api/generate"
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    payload = {"model": model, "prompt": full_prompt, "stream": False}
    if use_json_format:
        payload["format"] = "json"

    if debug_mode:
        print(f"🐞 [偵錯模式] 正在使用模型 '{model}' 透過 API: {generate_url}")
    else:
        print(f"💻 正在使用本地 Ollama 模型 '{model}'...")

    try:
        response = requests.post(generate_url, data=json.dumps(payload), timeout=120)
        response.raise_for_status()
        
        response_text = response.text.strip()
        last_json_str = next((line for line in reversed(response_text.splitlines()) if line.strip()), None)
        
        if not last_json_str:
            if debug_mode: print("🐞 [偵錯模式] AI 模型返回的原始 HTTP 回應為空或無效。")
            return None

        response_data = json.loads(last_json_str)
        content = response_data.get('response', '')

        if debug_mode:
            print("\n" + "="*20 + " [偵錯模式] AI 原始回應 " + "="*20)
            print(f"收到的內容長度: {len(content)} 字元")
            print("--- 內容開始 ---")
            print(content)
            print("--- 內容結束 ---")
            print("="*61 + "\n")

        if not content.strip():
            print("\n❌ 嚴重錯誤：本地 AI 模型返回了空內容！很可能是硬體資源不足。請嘗試更換一個更小的模型。\n")
            return None

        if use_json_format:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return match.group(0)
            else:
                if debug_mode: print("🐞 [偵錯模式] 在 AI 回應中未找到有效的 JSON 結構。")
                return None
        return content
        
    except requests.exceptions.RequestException as e:
        if debug_mode: print(f"🐞 [偵錯模式] 與本地 Ollama 連接時發生錯誤: {e}")
        raise e
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        if debug_mode: print(f"🐞 [偵錯模式] 解析本地 Ollama 原始回應時發生錯誤: {e}\n   收到的原始回應: {response.text}")
        return None
