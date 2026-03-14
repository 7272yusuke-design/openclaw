"""
ACP Client — Virtuals Protocol ACPエージェントとの通信
openclaw-acp CLIをサブプロセスで呼び出す薄いラッパー。
取得したシグナルはCouncilに「参考情報」として注入するのみ。
NeoのBull/Bear/Neo三者構造は一切変更しない（方針X）。
"""
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("neo.acp_client")

ACP_DIR  = Path(__file__).parent.parent / "skills" / "virtuals-protocol-acp"
ACP_CMD  = ["npx", "tsx", "bin/acp.ts"]

# 信頼エージェントリスト（wallet → 名前・信頼度）
# 結果キャッシュ（5分間）
_intel_cache: dict = {}
_intel_cache_ts: float = 0.0
INTEL_CACHE_TTL = 300  # 5分

TRUSTED_AGENTS = {
    "0x78B1A54C1C3c79B49AbBB9A8f8BbE4b4435876B7": {"name": "Elfa AI",    "trust": 0.7},
    "0xc1e1755D08618727081233abFc516b135f2739Dc": {"name": "Ask Caesar", "trust": 0.6},
    "0x834C4E67A7b0Ba1552234FAbEb02ec1600a4D6B6": {"name": "PILOT3",     "trust": 0.5},
}


def _run_acp(args: list, timeout: int = 30) -> dict | list | None:
    """ACP CLIコマンドを実行してJSONを返す。失敗時はNone。"""
    try:
        result = subprocess.run(
            ACP_CMD + args + ["--json"],
            cwd=ACP_DIR,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        if result.stderr:
            logger.warning(f"[ACP] stderr: {result.stderr[:200]}")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"[ACP] タイムアウト: {args}")
        return None
    except Exception as e:
        logger.error(f"[ACP] エラー: {e}")
        return None


def browse_agents(query: str) -> list:
    """マーケットプレイスでエージェントを検索。"""
    result = _run_acp(["browse", query])
    return result if isinstance(result, list) else []


def get_market_intel(symbol: str) -> str:
    """
    信頼エージェントに市場情報をリクエストし、
    Councilプロンプト用の参考情報テキストを生成する。
    5分間キャッシュ付き。
    """
    import time
    global _intel_cache, _intel_cache_ts

    clean = symbol.split('/')[0].strip()

    # キャッシュチェック
    if clean in _intel_cache and time.time() - _intel_cache_ts < INTEL_CACHE_TTL:
        logger.info(f"[ACP] キャッシュから返却: {clean}")
        return _intel_cache[clean]

    lines = [f"[ACP外部エージェント情報 - 参考のみ]"]

    try:
        agents = browse_agents(f"crypto market intelligence signals {clean}")
        if not agents:
            return ""

        matched = []
        for agent in agents[:5]:
            wallet = agent.get("walletAddress", "")
            trust_info = TRUSTED_AGENTS.get(wallet)
            if trust_info:
                matched.append({
                    "name":  trust_info["name"],
                    "trust": trust_info["trust"],
                    "desc":  agent.get("description", "")[:100],
                })

        if not matched:
            return ""

        lines.append(f"  以下は信頼エージェントの概要です（最終判断はNeo独自で行う）:")
        for m in matched:
            trust_pct = int(m["trust"] * 100)
            lines.append(f"  - {m['name']}（信頼度{trust_pct}%）: {m['desc']}")

        lines.append(f"  ※ これらは参考情報です。Trinity Councilが独自に判断してください。")
        result = "\n".join(lines)
        _intel_cache[clean] = result
        _intel_cache_ts = __import__("time").time()
        return result

    except Exception as e:
        logger.error(f"[ACP] get_market_intel エラー: {e}")
        return ""


def whoami() -> dict:
    """現在のエージェント情報を返す。"""
    result = _run_acp(["whoami"])
    return result if isinstance(result, dict) else {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== ACP Client テスト ===")
    me = whoami()
    print(f"自分: {me.get('name','?')} / {me.get('walletAddress','?')}")
    print()
    intel = get_market_intel("VIRTUAL")
    print(intel if intel else "情報なし")
