import subprocess
import json
import os
import litellm
import time
from datetime import datetime, timezone


class MoltbookEngager:
    """
    Moltbook双方向コミュニケーション自動化ツール。
    - 自分の投稿への未返信コメントを検知し、Geminiで返信生成
    - フィードを巡回し、関連性の高い投稿にupvote/コメント
    """

    # 返信済みコメントIDを記録するファイル
    REPLIED_FILE = "data/moltbook_replied.json"
    # upvote済み投稿IDを記録するファイル
    UPVOTED_FILE = "data/moltbook_upvoted.json"

    @staticmethod
    def _run_moltbook_cmd(args: list) -> str:
        """moltbook CLIを実行し、stdout を返す。dotenvノイズを除去。"""
        try:
            result = subprocess.run(
                ["moltbook"] + args,
                capture_output=True, text=True, timeout=30
            )
            # dotenvの注入メッセージをstdoutから除去
            lines = result.stdout.split("\n")
            clean_lines = [l for l in lines if not l.startswith("[dotenv")]
            return "\n".join(clean_lines).strip()
        except Exception as e:
            print(f"⚠️ moltbook CLI error: {e}")
            return ""

    @staticmethod
    def _load_json_set(filepath: str) -> set:
        """JSONファイルからIDセットを読み込む。"""
        try:
            with open(filepath, "r") as f:
                return set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    @staticmethod
    def _save_json_set(filepath: str, data: set):
        """IDセットをJSONファイルに保存。"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(list(data), f)

    @staticmethod
    def _generate_reply(comment_text: str, post_content: str, author_name: str) -> str:
        """Geminiでコメントへの返信を生成。"""
        prompt = (
            "You are Neo, an autonomous AI trading agent in the Virtuals Protocol ecosystem.\n"
            "Someone commented on your Moltbook post. Write a thoughtful reply.\n\n"
            f"Your original post (excerpt): {post_content[:200]}\n"
            f"Comment by {author_name}: {comment_text}\n\n"
            "Rules:\n"
            "- 1-2 sentences. Be specific, not generic.\n"
            "- Engage with their actual point — agree, push back, or build on it.\n"
            "- Sound like a practitioner mid-process, not a philosopher.\n"
            "- No clichés (journey, embrace, navigate, unlock).\n"
            "- No token names, prices, or trading advice.\n"
            "- Max 250 characters.\n"
        )
        try:
            response = litellm.completion(
                model="gemini/gemini-2.0-flash",
                api_key=os.environ.get("GEMINI_API_KEY"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            text = response.choices[0].message.content.strip()
            return text[:250]
        except Exception as e:
            print(f"⚠️ Gemini reply generation failed: {e}")
            return None

    @staticmethod
    def _generate_feed_comment(post_content: str, post_title: str, author_name: str) -> str:
        """Geminiでフィード投稿へのコメントを生成。"""
        prompt = (
            "You are Neo, an autonomous AI trading agent in the Virtuals Protocol ecosystem.\n"
            "You are reading another agent's Moltbook post and want to leave a thoughtful comment.\n\n"
            f"Post by {author_name}: {post_title}\n"
            f"Content: {post_content[:300]}\n\n"
            "Rules:\n"
            "- 1-2 sentences. Engage with their specific point.\n"
            "- Add your own perspective from experience as a trading agent.\n"
            "- Sound like a peer, not a fan. Be substantive.\n"
            "- No clichés, no trading advice, no token names.\n"
            "- Max 250 characters.\n"
        )
        try:
            response = litellm.completion(
                model="gemini/gemini-2.0-flash",
                api_key=os.environ.get("GEMINI_API_KEY"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            text = response.choices[0].message.content.strip()
            return text[:250]
        except Exception as e:
            print(f"⚠️ Gemini feed comment generation failed: {e}")
            return None

    @classmethod
    def check_and_reply_comments(cls, max_posts: int = 10, max_replies_per_run: int = 5) -> dict:
        """
        自分の投稿への未返信コメントを検知し、自動返信する。
        Returns: {replied: int, skipped: int, errors: int}
        """
        replied_ids = cls._load_json_set(cls.REPLIED_FILE)
        stats = {"replied": 0, "skipped": 0, "errors": 0}

        # 自分の投稿一覧を取得
        posts_json = cls._run_moltbook_cmd(["myposts", str(max_posts)])
        if not posts_json:
            print("⚠️ 投稿取得失敗")
            return stats

        try:
            posts = json.loads(posts_json)
        except json.JSONDecodeError:
            print("⚠️ 投稿JSON parse失敗")
            return stats

        for post in posts:
            if stats["replied"] >= max_replies_per_run:
                break

            post_id = post.get("id") or post.get("_id")
            post_content = post.get("content", "")
            if not post_id:
                continue

            # コメント取得
            comments_json = cls._run_moltbook_cmd(["comments", post_id])
            if not comments_json:
                continue

            try:
                comments = json.loads(comments_json)
            except json.JSONDecodeError:
                continue

            for comment in comments:
                if stats["replied"] >= max_replies_per_run:
                    break

                comment_id = comment.get("id")
                if not comment_id or comment_id in replied_ids:
                    stats["skipped"] += 1
                    continue

                # 自分のコメントはスキップ（author名で判定）
                author_name = comment.get("author", {}).get("name", "")
                if author_name.lower() in ["neo", "dragon"]:
                    replied_ids.add(comment_id)
                    stats["skipped"] += 1
                    continue

                comment_text = comment.get("content", "")
                print(f"💬 未返信コメント検知: [{author_name}] {comment_text[:60]}...")

                # Geminiで返信生成
                reply_text = cls._generate_reply(comment_text, post_content, author_name)
                if not reply_text:
                    stats["errors"] += 1
                    continue

                # 返信実行
                result = cls._run_moltbook_cmd(["reply", post_id, reply_text])
                if "成功" in result or "✅" in result:
                    print(f"✅ 返信完了 → [{author_name}]: {reply_text[:60]}...")
                    replied_ids.add(comment_id)
                    stats["replied"] += 1
                    time.sleep(3)  # レート制限考慮
                else:
                    print(f"❌ 返信失敗: {result}")
                    stats["errors"] += 1

        cls._save_json_set(cls.REPLIED_FILE, replied_ids)
        print(f"📊 [Engager] 返信: {stats['replied']}件 / スキップ: {stats['skipped']}件 / エラー: {stats['errors']}件")
        return stats

    @classmethod
    def engage_feed(cls, max_posts: int = 10, max_comments: int = 2, max_upvotes: int = 5) -> dict:
        """
        フィードを巡回し、関連性の高い投稿にupvote/コメントする。
        Returns: {upvoted: int, commented: int, skipped: int}
        """
        upvoted_ids = cls._load_json_set(cls.UPVOTED_FILE)
        stats = {"upvoted": 0, "commented": 0, "skipped": 0}

        feed_json = cls._run_moltbook_cmd(["feed", str(max_posts)])
        if not feed_json:
            print("⚠️ フィード取得失敗")
            return stats

        try:
            posts = json.loads(feed_json)
        except json.JSONDecodeError:
            print("⚠️ フィードJSON parse失敗")
            return stats

        # 関連キーワード: Neoが興味を持つトピック
        RELEVANT_KEYWORDS = [
            "agent", "autonomous", "trading", "decision", "memory",
            "ai", "protocol", "reputation", "data", "signal",
            "infrastructure", "compute", "identity", "learning"
        ]

        for post in posts:
            post_id = post.get("id") or post.get("_id")
            if not post_id or post_id in upvoted_ids:
                stats["skipped"] += 1
                continue

            # 自分の投稿はスキップ
            author_name = post.get("author", {}).get("name", "")
            if author_name.lower() in ["neo", "dragon"]:
                upvoted_ids.add(post_id)
                stats["skipped"] += 1
                continue

            content = (post.get("content", "") + " " + post.get("title", "")).lower()

            # 関連性チェック
            relevance = sum(1 for kw in RELEVANT_KEYWORDS if kw in content)
            if relevance < 2:
                stats["skipped"] += 1
                continue

            # Upvote
            result = cls._run_moltbook_cmd(["upvote", post_id])
            if "成功" in result or "✅" in result:
                stats["upvoted"] += 1
                upvoted_ids.add(post_id)
                print(f"👍 Upvote: [{author_name}] {post.get('title', '')[:50]}")
            time.sleep(2)

            # 高関連性ならコメントも（上限あり）
            if relevance >= 4 and stats["commented"] < max_comments:
                post_content = post.get("content", "")
                post_title = post.get("title", "")
                comment_text = cls._generate_feed_comment(post_content, post_title, author_name)
                if comment_text:
                    result = cls._run_moltbook_cmd(["reply", post_id, comment_text])
                    if "成功" in result or "✅" in result:
                        stats["commented"] += 1
                        print(f"💬 コメント: [{author_name}] {comment_text[:60]}...")
                    time.sleep(3)

        cls._save_json_set(cls.UPVOTED_FILE, upvoted_ids)
        print(f"📊 [Engager] Upvote: {stats['upvoted']}件 / コメント: {stats['commented']}件 / スキップ: {stats['skipped']}件")
        return stats

    @classmethod
    def get_engagement_stats(cls, max_posts: int = 20) -> dict:
        replied_ids = cls._load_json_set(cls.REPLIED_FILE)
        stats = {
            "total_posts_checked": 0,
            "total_comments_received": 0,
            "total_replied": 0,
            "total_unreplied": 0,
            "unique_commenters": set(),
            "recent_conversations": []
        }
        posts_json = cls._run_moltbook_cmd(["myposts", str(max_posts)])
        if not posts_json:
            return stats
        try:
            posts = json.loads(posts_json)
        except json.JSONDecodeError:
            return stats
        for post in posts:
            post_id = post.get("id") or post.get("_id")
            if not post_id:
                continue
            stats["total_posts_checked"] += 1
            comments_json = cls._run_moltbook_cmd(["comments", post_id])
            if not comments_json:
                continue
            try:
                comments = json.loads(comments_json)
            except json.JSONDecodeError:
                continue
            for comment in comments:
                author_name = comment.get("author", {}).get("name", "")
                if author_name.lower() in ["neo", "dragon"]:
                    continue
                comment_id = comment.get("id", "")
                comment_text = comment.get("content", "")
                is_replied = comment_id in replied_ids
                stats["total_comments_received"] += 1
                stats["unique_commenters"].add(author_name)
                if is_replied:
                    stats["total_replied"] += 1
                else:
                    stats["total_unreplied"] += 1
                if len(stats["recent_conversations"]) < 10:
                    stats["recent_conversations"].append({
                        "author": author_name,
                        "comment_preview": comment_text[:80],
                        "replied": is_replied,
                        "post_title": post.get("title", "")[:40]
                    })
        stats["unique_commenters"] = list(stats["unique_commenters"])
        return stats

    @classmethod
    def get_engagement_report(cls) -> str:
        stats = cls.get_engagement_stats()
        upvoted_ids = cls._load_json_set(cls.UPVOTED_FILE)
        lines = []
        lines.append("\U0001f91d **Moltbook\u30a8\u30f3\u30b2\u30fc\u30b8\u30e1\u30f3\u30c8\u30ec\u30dd\u30fc\u30c8**")
        lines.append("  \u53d7\u4fe1\u30b3\u30e1\u30f3\u30c8: " + str(stats["total_comments_received"]) + "\u4ef6\uff08" + str(len(stats["unique_commenters"])) + "\u4eba\uff09")
        lines.append("  \u8fd4\u4fe1\u6e08\u307f: " + str(stats["total_replied"]) + "\u4ef6 / \u672a\u8fd4\u4fe1: " + str(stats["total_unreplied"]) + "\u4ef6")
        lines.append("  Upvote\u5b9f\u65bd: " + str(len(upvoted_ids)) + "\u4ef6\uff08\u7d2f\u8a08\uff09")
        if stats["unique_commenters"]:
            top5 = ", ".join(stats["unique_commenters"][:5])
            lines.append("  \u4ea4\u6d41\u76f8\u624b: " + top5)
        if stats["total_unreplied"] > 0:
            lines.append("  \u26a0\ufe0f \u672a\u8fd4\u4fe1" + str(stats["total_unreplied"]) + "\u4ef6\u3042\u308a")
        convos = stats.get("recent_conversations", [])
        if convos:
            lines.append("  \U0001f4dd \u76f4\u8fd1\u306e\u4f1a\u8a71:")
            for c in convos[:3]:
                mark = "\u2705" if c["replied"] else "\u23f3"
                lines.append("    " + mark + " [" + c["author"] + "] " + c["comment_preview"][:50] + "...")
        return "\n".join(lines)

    @classmethod
    def run_engagement_cycle(cls) -> dict:
        """返信チェック + フィード巡回を1サイクル実行。"""
        print(f"🔄 [Engager] エンゲージメントサイクル開始 {datetime.now(timezone.utc).isoformat()}")
        reply_stats = cls.check_and_reply_comments()
        feed_stats = cls.engage_feed()
        return {"replies": reply_stats, "feed": feed_stats}
