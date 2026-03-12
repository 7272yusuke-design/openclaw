import pandas as pd
import pandas_ta as ta

class NeoIndicators:
    @staticmethod
    def calculate_freqtrade_vibe(price_history: list):
        """
        freqtrade/technical の標準指標を計算し、Scoutが読みやすい形式に変換
        """
        if len(price_history) < 20:
            return {"status": "pending", "message": "データ蓄積中..."}

        df = pd.DataFrame(price_history, columns=['close'])
        
        # 指標計算 (freqtrade常用セット)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema20'] = ta.ema(df['close'], length=20)
        bbands = ta.bbands(df['close'], length=20, std=2)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        return {
            "rsi": round(latest['rsi'], 2),
            "trend": "Upward" if latest['ema9'] > latest['ema20'] else "Downward",
            "ema_cross": "Golden Cross" if (prev['ema9'] <= prev['ema20'] and latest['ema9'] > latest['ema20']) else "None",
            "bb_position": "Overbought" if latest['close'] > bbands['BBU_20_2.0'].iloc[-1] else ("Oversold" if latest['close'] < bbands['BBL_20_2.0'].iloc[-1] else "Neutral")
        }
