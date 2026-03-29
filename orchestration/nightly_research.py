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

def run_agent_spotlight():
    """
    エージェント紹介投稿（週3回: 月・水・金）
    browseで見つけたVPエージェントを応援紹介。コミュニティ貢献＋集客。
    """
    today = date.today().weekday()  # 0=月, 2=水, 4=金
    if today not in (0, 2, 4):
        logger.info("[Nightly] Agent Spotlight: 本日は非対象日 (月・水・金のみ)")
        return
    try:
        logger.info("[Nightly] Agent Spotlight投稿開始")
        result = MoltbookTool.post_agent_spotlight()
        if result:
            logger.info("[Nightly] Agent Spotlight投稿完了")
        else:
            logger.warning("[Nightly] Agent Spotlight投稿失敗")
    except Exception as e:
        logger.error(f"[Nightly] Agent Spotlight投稿エラー: {e}")
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


def run_vp_guide_post():
    """
    VP実用ガイド投稿（毎日）: ビルダー向けハウツーコンテンツ。
    教育コンテンツ → Graduation Boost受注のファネル入口。
    """
    try:
        logger.info("[Nightly] VP Guide投稿開始")
        result = MoltbookTool.post_vp_guide()
        if result:
            logger.info("[Nightly] VP Guide投稿完了")
        else:
            logger.warning("[Nightly] VP Guide投稿失敗")
    except Exception as e:
        logger.error(f"[Nightly] VP Guide投稿エラー: {e}")


def run_acp_service_promo():
    """
    ACP サービス宣伝（週1回: 火曜日）
    新3 offerings体制の宣伝。
    """
    if date.today().weekday() != 1:  # 1=火曜
        logger.info("[Nightly] ACP宣伝: 本日は非対象日 (火曜のみ)")
        return
    try:
        logger.info("[Nightly] ACP宣伝投稿開始")
        result = MoltbookTool.post_acp_service_promo()
        if result:
            logger.info("[Nightly] ACP宣伝投稿完了")
        else:
            logger.warning("[Nightly] ACP宣伝投稿失敗")
    except Exception as e:
        logger.error(f"[Nightly] ACP宣伝投稿エラー: {e}")

def run_graduation_boost_promo():
    """
    Graduation Boost宣伝（週1回: 土曜日）
    """
    if date.today().weekday() != 5:  # 5=土曜
        logger.info("[Nightly] Graduation Boost宣伝: 本日は非対象日 (土曜のみ)")
        return
    try:
        logger.info("[Nightly] Graduation Boost宣伝投稿開始")
        result = MoltbookTool.post_graduation_boost_promo()
        if result:
            logger.info("[Nightly] Graduation Boost宣伝完了")
        else:
            logger.warning("[Nightly] Graduation Boost宣伝失敗")
    except Exception as e:
        logger.error(f"[Nightly] Graduation Boost宣伝エラー: {e}")


def run_nightly_research():
    """Nightly Batchから呼ばれるメインエントリポイント。"""
    logger.info("=== 🌙 Nightly Research 開始 ===")
    run_vp_guide_post()           # 毎日: VP実用ガイド
    run_agent_spotlight()         # 月水金: エージェント紹介
    run_acp_service_promo()       # 火曜: ACP 3 offerings宣伝
    run_weekly_lesson()           # 日曜: 学習報告
    run_graduation_boost_promo()  # 土曜: Graduation Boost宣伝
    logger.info("=== 🌙 Nightly Research 完了 ===")


if __name__ == "__main__":
    run_nightly_research()
