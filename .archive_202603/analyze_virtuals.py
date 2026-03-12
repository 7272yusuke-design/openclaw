import pandas as pd
import matplotlib.pyplot as plt
import datetime

# Virtuals Protocol 参加エージェント推移の予測シミュレーションデータ作成
# (現在は実測値ではないため、トレンドを模したシミュレーション値)
dates = pd.date_range(start='2026-02-01', periods=18, freq='D')
agent_counts = [10, 12, 15, 22, 28, 35, 42, 58, 75, 98, 125, 160, 210, 280, 350, 480, 620, 800]

df = pd.DataFrame({'Date': dates, 'Agents': agent_counts})

# グラフの描画
plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Agents'], marker='o', linestyle='-', color='#00a8ff', linewidth=2)
plt.fill_between(df['Date'], df['Agents'], color='#00a8ff', alpha=0.1)

plt.title('Virtuals Protocol - Registered Agents Growth', fontsize=16, pad=20)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Number of Agents', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.xticks(rotation=45)
plt.tight_layout()

# 保存
plt.savefig('virtuals_growth.png')
print("Graph saved as virtuals_growth.png")
