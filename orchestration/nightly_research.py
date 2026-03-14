"""
Nightly Research — 夜間バッチで実行される洞察投稿・学習報告
run_trigger.py の _run_nightly_batch() から呼ばれる
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, date

BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
sys.path.append(str(BASE_DIR))

from core.blackboard import NeoBlackboard
from core.memory_db import NeoMemoryDB
from tools.moltbook_tool import MoltbookTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("neo.nightly")

def run_insight_post():
    """
    洞察投稿（週3回: 月・水・金）
    Blackboardの状況からトピックを自動選定してMoltbookに投稿。
    """
    today = date.today().weekday()  # 0=月, 2=水, 4=金
    if today not in (0, 2, 4):
        logger.info("[Nightly] 洞察投稿: 本日は非対象日 (月・水・金のみ)")
        return

    try:
        board = NeoBlackboard.load()
        opps = board.get("strategic_intel", {}).get("active_opportunities",
               board.get("active_opportunities", {}))
        perf = board.get("performance_summary", {})

        # トピックと背景情報を自動生成
        opp_count = len(opps)
        accuracy = perf.get("accuracy_score", 0.0)
        total_trades = perf.get("total_evaluated_trades", 0)

        # 最高Sharpe銘柄を特定
        top_symbol = None
        top_sharpe = 0.0
        for sym, data in opps.items():
            if data.get("sharpe", 0) > top_sharpe:
                top_sharpe = data["sharpe"]
                top_symbol = sym

        if top_symbol:
            topic = f"{top_symbol}のアルファシグナルとVP経済圏の動向"
            context = (
                f"現在{opp_count}件のAlpha機会を検知中。"
                f"最注目: {top_symbol} (Sharpe={top_sharpe:.1f})。"
                f"Neo累計勝率: {accuracy}% ({total_trades}件)。"
                f"今日の日付: {date.today()}"
            )
        else:
            topic = "VP経済圏の現在地と今後の展望"
            context = (
                f"現在Alpha機会は検知されていない静観フェーズ。"
                f"Neo累計勝率: {accuracy}% ({total_trades}件)。"
                f"今日の日付: {date.today()}"
            )

        logger.info(f"[Nightly] 洞察投稿開始: {topic}")
        result = MoltbookTool.post_insight(topic=topic, context=context)
        if result:
            logger.info("[Nightly] 洞察投稿完了")
        else:
            logger.warning("[Nightly] 洞察投稿失敗")

    except Exception as e:
        logger.error(f"[Nightly] 洞察投稿エラー: {e}")


def run_weekly_lesson():
    """
    学習報告（週1回: 日曜日）
    ChromaDBの直近教訓からNeoらしい振り返りを投稿。
    """
    if date.today().weekday() != 6:  # 6=日曜
        logger.info("[Nightly] 学習報告: 本日は非対象日 (日曜のみ)")
        return

    try:
        memory = NeoMemoryDB()
        lessons = memory.recall_lessons(n_results=3)

        if not lessons:
            logger.info("[Nightly] 学習報告: 教訓データなし、スキップ")
            return

        lesson_text = " / ".join([l[:60] for l in lessons])
        context = f"直近の記憶から抽出した教訓: {lesson_text}"

        logger.info("[Nightly] 学習報告投稿開始")
        result = MoltbookTool.post_weekly_lesson(
            lesson="今週のNeoの学習まとめ",
            context=context
        )
        if result:
            logger.info("[Nightly] 学習報告完了")
        else:
            logger.warning("[Nightly] 学習報告失敗")

    except Exception as e:
        logger.error(f"[Nightly] 学習報告エラー: {e}")


def run_nightly_research():
    """Nightly Batchから呼ばれるメインエントリポイント。"""
    logger.info("=== 🌙 Nightly Research 開始 ===")
    run_insight_post()
    run_weekly_lesson()
    logger.info("=== 🌙 Nightly Research 完了 ===")


if __name__ == "__main__":
    run_nightly_research()
