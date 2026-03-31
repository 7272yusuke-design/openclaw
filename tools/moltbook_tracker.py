"""
C.2: Moltbook反響トラッキング
- 定期的にNeo自身の投稿のengagementを取得
- data/moltbook_stats.json に蓄積
- Discord日次サマリーに反映
"""
import subprocess
import json
import os
import time
import logging

logger = logging.getLogger("neo.moltbook_tracker")

STATS_PATH = "data/moltbook_stats.json"
AGENT_NAME = "neoautonomous"

JS_FETCH_STATS = """
import('moltbook').then(async m => {
    const dotenv = await import('dotenv');
    dotenv.default.config({path: '/docker/openclaw-taan/data/.openclaw/workspace/.env'});
    const client = new m.Moltbook({apiKey: process.env.MOLTBOOK_API_KEY});
    const profile = await client.getAgentProfile('""" + AGENT_NAME + """');
    const agent = profile.agent;
    const posts = profile.recentPosts || [];
    const total_upvotes = posts.reduce((s, p) => s + (p.upvotes || 0), 0);
    const total_comments = posts.reduce((s, p) => s + (p.comment_count || 0), 0);
    const best = posts.reduce((b, p) => (p.upvotes || 0) > (b.upvotes || 0) ? p : b, {upvotes: 0});
    console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        karma: agent.karma,
        follower_count: agent.follower_count,
        following_count: agent.following_count,
        posts_count: agent.posts_count,
        recent_posts_count: posts.length,
        total_upvotes: total_upvotes,
        total_comments: total_comments,
        avg_upvotes: posts.length > 0 ? (total_upvotes / posts.length).toFixed(2) : 0,
        best_post: {
            preview: (best.content_preview || '').substring(0, 60),
            upvotes: best.upvotes || 0,
            comments: best.comment_count || 0,
            date: best.created_at || ''
        },
        posts_detail: posts.map(p => ({
            preview: (p.content_preview || '').substring(0, 80),
            upvotes: p.upvotes || 0,
            comments: p.comment_count || 0,
            submolt: (p.submolt || {}).name || 'unknown',
            date: p.created_at || ''
        }))
    }));
}).catch(e => { console.error('Error:', e.message); process.exit(1); });
"""

def fetch_engagement_stats() -> dict:
    """MoltbookからNeoのengagement統計を取得"""
    try:
        result = subprocess.run(
            ["node", "--input-type=module"],
            input=JS_FETCH_STATS,
            capture_output=True, text=True, timeout=30,
            cwd="/docker/openclaw-taan/data/.openclaw/workspace"
        )
        # dotenvのログを除いてJSONを抽出
        for line in result.stdout.splitlines():
            if line.startswith('{'):
                return json.loads(line)
        logger.error(f"No JSON in output: {result.stdout[:200]}")
        return {}
    except Exception as e:
        logger.error(f"fetch_engagement_stats error: {e}")
        return {}


def save_stats(stats: dict):
    """統計をJSONに追記保存"""
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    history = []
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH) as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(stats)
    # 最新90件のみ保持
    history = history[-90:]
    with open(STATS_PATH, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_latest_stats() -> dict:
    """最新の統計を返す"""
    if not os.path.exists(STATS_PATH):
        return {}
    try:
        with open(STATS_PATH) as f:
            history = json.load(f)
        return history[-1] if history else {}
    except Exception:
        return {}


def get_growth_summary() -> str:
    """成長サマリーを文字列で返す（Discord報告用）"""
    if not os.path.exists(STATS_PATH):
        return "📊 Moltbook統計: データなし"
    try:
        with open(STATS_PATH) as f:
            history = json.load(f)
        if not history:
            return "📊 Moltbook統計: データなし"

        latest = history[-1]
        prev = history[-2] if len(history) >= 2 else latest

        karma_diff = latest['karma'] - prev['karma']
        follower_diff = latest['follower_count'] - prev['follower_count']

        lines = [
            "📊 **Moltbook反響レポート**",
            f"  karma: {latest['karma']} ({'+' if karma_diff >= 0 else ''}{karma_diff})",
            f"  フォロワー: {latest['follower_count']} ({'+' if follower_diff >= 0 else ''}{follower_diff})",
            f"  総投稿数: {latest['posts_count']}",
            f"  直近avg upvotes: {latest['avg_upvotes']}",
            f"  直近avg comments: {latest['total_comments']}",
        ]
        if latest.get('best_post', {}).get('upvotes', 0) > 0:
            bp = latest['best_post']
            lines.append(f"  最高投稿: {bp['upvotes']}upvotes — {bp['preview'][:40]}...")
        return "\n".join(lines)
    except Exception as e:
        return f"📊 Moltbook統計エラー: {e}"



def analyze_best_topics() -> dict:
    """
    蓄積済みposts_detailからトピック傾向を分析。
    submolt別・キーワード別のavg upvotesを返す。
    """
    if not os.path.exists(STATS_PATH):
        return {}
    try:
        with open(STATS_PATH) as f:
            history = json.load(f)
    except Exception:
        return {}

    # 全投稿を収集（重複排除）
    seen = set()
    all_posts = []
    for h in history:
        for p in h.get("posts_detail", []):
            key = p.get("preview", "")[:40]
            if key and key not in seen:
                seen.add(key)
                all_posts.append(p)

    if not all_posts:
        return {}

    # submolt別集計
    submolt_stats = {}
    for p in all_posts:
        sm = p.get("submolt", "unknown")
        if sm not in submolt_stats:
            submolt_stats[sm] = {"count": 0, "upvotes": 0, "comments": 0}
        submolt_stats[sm]["count"] += 1
        submolt_stats[sm]["upvotes"] += p.get("upvotes", 0)
        submolt_stats[sm]["comments"] += p.get("comments", 0)

    submolt_ranking = sorted(
        [{"submolt": k, "count": v["count"],
          "avg_upvotes": round(v["upvotes"] / v["count"], 2),
          "avg_comments": round(v["comments"] / v["count"], 2)}
         for k, v in submolt_stats.items()],
        key=lambda x: x["avg_upvotes"], reverse=True
    )

    # キーワード傾向（upvotes>=1の投稿から抽出）
    high_posts = [p for p in all_posts if p.get("upvotes", 0) >= 1]
    low_posts  = [p for p in all_posts if p.get("upvotes", 0) == 0]

    return {
        "total_posts_analyzed": len(all_posts),
        "submolt_ranking": submolt_ranking,
        "best_submolt": submolt_ranking[0]["submolt"] if submolt_ranking else "agentfinance",
        "high_engagement_previews": [p["preview"][:60] for p in high_posts[:5]],
        "low_engagement_previews":  [p["preview"][:60] for p in low_posts[:3]],
    }


def get_topic_recommendation() -> str:
    """投稿トピック推奨をテキストで返す（moltbook_tool.py用）"""
    analysis = analyze_best_topics()
    if not analysis:
        return ""
    lines = [f"[M.3分析] {analysis['total_posts_analyzed']}件分析済み"]
    for s in analysis["submolt_ranking"]:
        lines.append(f"  {s['submolt']}: avg {s['avg_upvotes']}up ({s['count']}件)")
    if analysis["high_engagement_previews"]:
        lines.append("高反響パターン: " + " / ".join(analysis["high_engagement_previews"][:2]))
    return "\n".join(lines)


def run_tracking():
    """反響取得 → 保存 → サマリー返却"""
    logger.info("[MoltbookTracker] 反響取得中...")
    stats = fetch_engagement_stats()
    if stats:
        save_stats(stats)
        logger.info(f"[MoltbookTracker] karma={stats.get('karma')} followers={stats.get('follower_count')} avg_upvotes={stats.get('avg_upvotes')}")
    return get_growth_summary()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_tracking())
