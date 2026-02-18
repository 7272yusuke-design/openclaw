from bs4 import BeautifulSoup
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd

# 感情分析用の辞書をダウンロード（初回のみ）
nltk.download('vader_lexicon')

# サンプルデータ（Webから取得したニュース記事の見出しを想定）
news_headlines = [
    "Virtuals Protocol experiences massive surge in user adoption",
    "Investors concerned about the sustainability of AI agent economy",
    "New SDK release makes agent deployment easier than ever",
    "Market shows volatility as major exchanges adjust token listings",
    "Neo the AI agent successfully integrates advanced data analysis skills"
]

# 感情分析の実行
sia = SentimentIntensityAnalyzer()
results = []

for headline in news_headlines:
    score = sia.polarity_scores(headline)
    # 複合スコア（compound）でポジティブ・ネガティブを判定
    sentiment = 'Positive' if score['compound'] >= 0.05 else 'Negative' if score['compound'] <= -0.05 else 'Neutral'
    results.append({
        'Headline': headline,
        'Compound Score': score['compound'],
        'Sentiment': sentiment
    })

df = pd.DataFrame(results)

# 結果の表示
print("### AI News Sentiment Analysis Results ###\n")
print(df[['Headline', 'Sentiment', 'Compound Score']])

# ポジティブ率の計算
positive_rate = (df['Sentiment'] == 'Positive').mean() * 100
print(f"\nOverall Positive Sentiment Rate: {positive_rate:.1f}%")
