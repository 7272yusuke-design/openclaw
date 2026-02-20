
import sys
import nltk
from nltk.corpus import stopwords
from collections import Counter
import re

# NLTKデータのダウンロード（初回のみ必要）
try:
    nltk.data.find('tokenizers/punkt')
except Exception:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except Exception:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt_tab')
except Exception:
    nltk.download('punkt_tab')

def extract_keywords(text, num_keywords=5):
    # テキストを小文字に変換し、非英数字を除去
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '', text) # 日本語対応

    # 単語に分割
    words = nltk.word_tokenize(text)
    
    # ストップワードの除去
    stop_words = set(stopwords.words('english'))
    # 日本語のストップワードも考慮する場合は、別途リストを追加
    # stop_words.update(['は', 'が', 'を', 'に', 'で', 'と', 'も', ...])

    filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # 頻度をカウント
    word_counts = Counter(filtered_words)
    
    # 最も頻繁に出現するキーワードを抽出
    keywords = [word for word, count in word_counts.most_common(num_keywords)]
    
    print(f"Keywords: {keywords}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python keyword_extraction.py \"<text to analyze>\"")
        sys.exit(1)
    
    text = sys.argv[1]
    extract_keywords(text)
