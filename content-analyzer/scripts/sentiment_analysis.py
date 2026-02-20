
import sys
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# NLTKデータのダウンロード（初回のみ必要）
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except Exception: # 元: nltk.downloader.DownloadError
    nltk.download('vader_lexicon')

def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    vs = analyzer.polarity_scores(text)
    
    sentiment = "Neutral"
    if vs['compound'] >= 0.05:
        sentiment = "Positive"
    elif vs['compound'] <= -0.05:
        sentiment = "Negative"
        
    print(f"Sentiment Score: {vs}")
    print(f"Overall Sentiment: {sentiment}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python sentiment_analysis.py \"<text to analyze>\"")
        sys.exit(1)
    
    text = sys.argv[1]
    analyze_sentiment(text)
