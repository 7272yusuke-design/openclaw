import backtrader as bt
import pandas as pd
import pandas_ta as ta
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class SmartNeoStrategy(bt.Strategy):
    params = (('logic', 'rsi'),)
    def __init__(self):
        self.rsi = self.data.rsi
        self.ema9 = self.data.ema9
        self.ema20 = self.data.ema20
        self.bb_upper = self.data.bb_upper
        self.bb_lower = self.data.bb_lower
    def next(self):
        if self.p.logic == 'ema_cross':
            if not self.position:
                if self.ema9[0] > self.ema20[0] and self.ema9[-1] <= self.ema20[-1]: self.buy()
            elif self.ema9[0] < self.ema20[0]: self.close()
        elif self.p.logic == 'bb_reversal':
            if not self.position:
                if self.data.close[0] < self.bb_lower[0]: self.buy()
            elif self.data.close[0] > self.bb_upper[0]: self.close()
        else:
            if not self.position:
                if self.rsi[0] < 30: self.buy()
            elif self.rsi[0] > 70: self.close()

def run_neo_backtest(csv_path, initial_cash=1000.0, logic='rsi'):
    if not os.path.exists(csv_path): return {"final_value": initial_cash, "chart_path": None}
    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema9'] = ta.ema(df['close'], length=9)
    df['ema20'] = ta.ema(df['close'], length=20)
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'], df['bb_lower'] = bb['BBU_20_2.0'], bb['BBL_20_2.0']
    df.fillna(0, inplace=True)
    class ExtendedPandasData(bt.feeds.PandasData):
        lines = ('rsi', 'ema9', 'ema20', 'bb_upper', 'bb_lower')
        params = tuple((l, -1) for l in lines)
    cerebro = bt.Cerebro()
    cerebro.adddata(ExtendedPandasData(dataname=df))
    cerebro.addstrategy(SmartNeoStrategy, logic=logic)
    cerebro.broker.setcash(initial_cash)
    cerebro.run()
    output_dir = "/docker/openclaw-taan/data/.openclaw/workspace/vault/reports"
    os.makedirs(output_dir, exist_ok=True)
    chart_path = os.path.join(output_dir, "latest_backtest.png")
    fig = cerebro.plot(style='candlestick')[0][0]
    fig.savefig(chart_path)
    plt.close('all')
    return {"final_value": cerebro.broker.getvalue(), "chart_path": chart_path}
