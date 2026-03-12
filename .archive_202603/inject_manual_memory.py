from core.memory_db import NeoMemoryDB

def inject_lesson():
    db = NeoMemoryDB()
    
    # 司令官がネオに教えたい「空白期間の重要な教訓」をここに書く
    lesson_content = """
    【司令官からの特別教訓: 2026年3月上旬の相場変動について】
    3月5日から10日にかけて、AIXBTやVIRTUALにおいて急激なボラティリティの増加が見られた。
    特に、ScoutAgentが「Accumulating」を検知した直後、短絡的な「BUY」判断が裏目に出る（ダマシ）ケースが散見された。
    今後の教訓として、クジラの蓄積サインが出た場合でも、Backtestの勝率が著しく低い（またはデータ不足）の場合は、断固として「WAIT」を選択し、リスク回避を最優先とすること。
    """
    
    db.store(
        content=lesson_content,
        metadata={"source": "commander_manual_injection", "date": "2026-03-12"}
    )
    print("✅ 司令官からの特別教訓をネオの脳（ChromaDB）に直接刻み込みました。")

if __name__ == "__main__":
    inject_lesson()
