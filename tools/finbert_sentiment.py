"""
K.1: FinBERTセンチメントスコア化
RSSニュースタイトルをFinBERTで定量スコアに変換してSentimentAgentに注入する。
モデルは初回のみダウンロード、以降はキャッシュを使用。
"""

import time
from typing import Optional

_pipe = None
_pipe_load_time = 0
_CACHE_SEC = 3600  # パイプラインは1時間キャッシュ

def _get_pipeline():
    """FinBERTパイプラインをシングルトンで返す。"""
    global _pipe, _pipe_load_time
    now = time.time()
    if _pipe is None or (now - _pipe_load_time) > _CACHE_SEC:
        try:
            from transformers import pipeline
            _pipe = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                device=-1,  # CPU
            )
            _pipe_load_time = now
        except Exception as e:
            print(f"⚠️ FinBERT pipeline load failed: {e}")
            _pipe = None
    return _pipe


def score_texts(texts: list[str]) -> list[dict]:
    """
    テキストリストをFinBERTでスコアリング。
    Returns: [{"label": "positive"|"negative"|"neutral", "score": float}, ...]
    失敗時は空リストを返す。
    """
    if not texts:
        return []
    pipe = _get_pipeline()
    if pipe is None:
        return []
    try:
        results = pipe(texts, truncation=True, max_length=512)
        return results
    except Exception as e:
        print(f"⚠️ FinBERT scoring failed: {e}")
        return []


def get_finbert_score(texts: list[str]) -> dict:
    """
    テキストリストの集計センチメントスコアを返す。

    Returns:
        {
            "score": float,        # -1.0(最悪) ~ +1.0(最良)
            "label": str,          # "positive" | "negative" | "neutral"
            "positive_ratio": float,
            "negative_ratio": float,
            "neutral_ratio": float,
            "count": int,
            "details": list[dict]  # 各テキストの結果
        }
    """
    empty = {
        "score": 0.0, "label": "neutral",
        "positive_ratio": 0.0, "negative_ratio": 0.0, "neutral_ratio": 0.0,
        "count": 0, "details": []
    }
    if not texts:
        return empty

    results = score_texts(texts)
    if not results:
        return empty

    pos = sum(1 for r in results if r["label"] == "positive")
    neg = sum(1 for r in results if r["label"] == "negative")
    neu = sum(1 for r in results if r["label"] == "neutral")
    total = len(results)

    # -1.0 ~ +1.0 のスコアに変換
    score = (pos - neg) / total

    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": round(score, 3),
        "label": label,
        "positive_ratio": round(pos / total, 3),
        "negative_ratio": round(neg / total, 3),
        "neutral_ratio": round(neu / total, 3),
        "count": total,
        "details": results
    }


def get_finbert_context_text(texts: list[str], source_label: str = "News") -> str:
    """
    SentimentAgentのプロンプトに注入するテキストを生成。
    """
    if not texts:
        return f"[FinBERT] No {source_label} texts to analyze."
    result = get_finbert_score(texts)
    if result["count"] == 0:
        return f"[FinBERT] {source_label} analysis unavailable."
    return (
        f"[FinBERT {source_label} Sentiment]\n"
        f"  Overall: {result['label'].upper()} (score: {result['score']:+.3f})\n"
        f"  Positive: {result['positive_ratio']*100:.0f}% | "
        f"Negative: {result['negative_ratio']*100:.0f}% | "
        f"Neutral: {result['neutral_ratio']*100:.0f}%\n"
        f"  Based on {result['count']} headlines"
    )


if __name__ == "__main__":
    # 動作確認用
    sample_texts = [
        "Virtuals Protocol sees record trading volume as AI agents gain traction",
        "AIXBT token crashes amid broader market selloff",
        "AI agent ecosystem expands with new developer tools",
        "Liquidity concerns mount for smaller DeFi protocols",
        "Base chain activity surges to new highs",
    ]
    print(get_finbert_context_text(sample_texts, "VP News"))
