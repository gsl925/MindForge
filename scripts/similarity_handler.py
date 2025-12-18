from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 載入一個輕量且高效的模型。模型會在第一次使用時自動下載。
# 'all-MiniLM-L6-v2' 是一個優秀的英文模型。
# 'paraphrase-multilingual-MiniLM-L12-v2' 支援多語言，包含中文。
MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def get_embedding(text: str):
    """為單段文本生成向量嵌入。"""
    return MODEL.encode(text)

def find_similar_items(target_embedding, existing_embeddings: list, threshold=0.7) -> list:
    """
    在現有嵌入中尋找與目標嵌入相似的項目。

    Args:
        target_embedding: 目標文本的嵌入向量。
        existing_embeddings: 一個包含 (id, embedding) 元組的列表。
        threshold: 相似度閾值。

    Returns:
        一個包含相似項目 id 和相似度分數的列表。
    """
    if not existing_embeddings:
        return []

    # 分離 ID 和嵌入向量
    ids, embeddings = zip(*existing_embeddings)
    
    # 計算餘弦相似度
    similarities = cosine_similarity([target_embedding], list(embeddings))[0]
    
    similar_items = []
    for i, score in enumerate(similarities):
        if score >= threshold:
            similar_items.append({"id": ids[i], "score": score})
            
    # 按分數從高到低排序
    return sorted(similar_items, key=lambda x: x['score'], reverse=True)

