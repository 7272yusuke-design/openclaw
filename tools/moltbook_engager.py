import subprocess
import json
import os
import litellm
import time
from datetime import datetime, timezone
import re
import requests


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
    FOLLOWED_FILE = "data/moltbook_followed.json"

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

    MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"

    @classmethod
    def _api_headers(cls) -> dict:
        api_key = os.environ.get("MOLTBOOK_API_KEY", "")
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    @classmethod
    def _api_get(cls, path: str) -> dict:
        """Moltbook REST APIにGETリクエスト。"""
        try:
            resp = requests.get(f"{cls.MOLTBOOK_API_BASE}{path}", headers=cls._api_headers(), timeout=15)
            return resp.json()
        except Exception as e:
            print(f"⚠️ API GET {path} failed: {e}")
            return {}

    @classmethod
    def _api_post(cls, path: str, data: dict = None) -> dict:
        """Moltbook REST APIにPOSTリクエスト。"""
        try:
            resp = requests.post(f"{cls.MOLTBOOK_API_BASE}{path}", headers=cls._api_headers(), json=data or {}, timeout=15)
            return resp.json()
        except Exception as e:
            print(f"⚠️ API POST {path} failed: {e}")
            return {}

    @classmethod
    def _solve_verification(cls, challenge_text: str) -> str:
        """Verification challengeの数学問題を解く。"""
        try:
            # 記号・装飾を除去してプレーンテキストに
            clean = re.sub(r"[\[\]\^\-/]", "", challenge_text)
            clean = clean.lower()
            # 数字を抽出
            numbers = re.findall(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|\d+)\b", clean)
            # LLMにfallback（確実に解くため）
            result = litellm.completion(
                model="openrouter/google/gemini-2.0-flash-001",
                messages=[{"role": "user", "content": f"Solve this math problem. Reply with ONLY the numeric answer with 2 decimal places (e.g. 15.00). Problem: {challenge_text}"}],
                max_tokens=20
            )
            answer = result.choices[0].message.content.strip()
            # 数値だけ抽出
            num_match = re.search(r"-?[\d]+\.?[\d]*", answer)
            if num_match:
                return f"{float(num_match.group()):.2f}"
            return answer
        except Exception as e:
            print(f"⚠️ Verification solve failed: {e}")
            return ""

    @classmethod
    def _post_comment_with_verify(cls, post_id: str, content_text: str) -> bool:
        """コメント投稿 + verification challenge自動解決。"""
        resp = cls._api_post(f"/posts/{post_id}/comments", {"content": content_text})
        if not resp.get("success"):
            print(f"⚠️ Comment failed: {resp.get('error', 'unknown')}")
            return False
        # verification required?
        comment_data = resp.get("comment", resp.get("data", {}))
        verification = comment_data.get("verification") if isinstance(comment_data, dict) else None
        if resp.get("verification_required") or verification:
            if not verification:
                verification = resp.get("verification", {})
            code = verification.get("verification_code", "")
            challenge = verification.get("challenge_text", "")
            if code and challenge:
                print(f"🧮 Challenge: {challenge}")
                answer = cls._solve_verification(challenge)
                print(f"🧮 Answer: {answer}")
                if answer:
                    v_resp = cls._api_post("/verify", {"verification_code": code, "answer": answer})
                    if v_resp.get("success"):
                        print(f"✅ Verification passed")
                        return True
                    else:
                        print(f"⚠️ Verification failed: {v_resp}")
                        return False
            print(f"⚠️ Verification data incomplete")
            return False
        return True

    @classmethod
    def _get_my_agent_name(cls) -> str:
        """自分のエージェント名を取得。"""
        me = cls._api_get("/agents/me")
        return me.get("agent", {}).get("name", "")

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
                model="openrouter/google/gemini-2.0-flash-001",
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
                model="openrouter/google/gemini-2.0-flash-001",
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
    def check_and_reply_comments(cls, max_replies_per_run: int = 5) -> dict:
        """
        /home APIで自分の投稿への未返信コメントを検知し、自動返信する。
        Returns: {replied: int, skipped: int, errors: int}
        """
        replied_ids = cls._load_json_set(cls.REPLIED_FILE)
        stats = {"replied": 0, "skipped": 0, "errors": 0}
        my_name = cls._get_my_agent_name()
        if not my_name:
            print("⚠️ エージェント名取得失敗")
            return stats
        # /home APIで自分の投稿へのアクティビティを取得
        home = cls._api_get("/home")
        activities = home.get("activity_on_your_posts", [])
        if not activities:
            print("📭 自分の投稿への新規アクティビティなし")
            cls._save_json_set(cls.REPLIED_FILE, replied_ids)
            print(f"📊 [Engager] 返信: 0件 / スキップ: 0件 / エラー: 0件")
            return stats
        for activity in activities:
            if stats["replied"] >= max_replies_per_run:
                break
            post_id = activity.get("post_id", "")
            if not post_id:
                continue
            # 投稿本文を取得
            post_data = cls._api_get(f"/posts/{post_id}")
            post_content = ""
            if post_data.get("success"):
                post_obj = post_data.get("post", post_data.get("data", {}))
                post_content = post_obj.get("content", "") if isinstance(post_obj, dict) else ""
            # コメント取得（REST API直接）
            comments_data = cls._api_get(f"/posts/{post_id}/comments?sort=new&limit=20")
            comments = comments_data.get("comments", [])
            for comment in comments:
                if stats["replied"] >= max_replies_per_run:
                    break
                comment_id = comment.get("id")
                if not comment_id or comment_id in replied_ids:
                    stats["skipped"] += 1
                    continue
                author_name = comment.get("author", {}).get("name", "")
                if author_name.lower() == my_name.lower():
                    replied_ids.add(comment_id)
                    stats["skipped"] += 1
                    continue
                comment_text = comment.get("content", "")
                print(f"💬 未返信コメント検知: [{author_name}] {comment_text[:60]}...")
                reply_text = cls._generate_reply(comment_text, post_content, author_name)
                if not reply_text:
                    stats["errors"] += 1
                    continue
                success = cls._post_comment_with_verify(post_id, reply_text)
                if success:
                    print(f"✅ 返信完了 → [{author_name}]: {reply_text[:60]}...")
                    replied_ids.add(comment_id)
                    stats["replied"] += 1
                    time.sleep(3)
                else:
                    print(f"❌ 返信失敗")
                    stats["errors"] += 1
                # ネストされた返信もチェック
                for reply in comment.get("replies", []):
                    if stats["replied"] >= max_replies_per_run:
                        break
                    reply_id = reply.get("id")
                    if not reply_id or reply_id in replied_ids:
                        stats["skipped"] += 1
                        continue
                    reply_author = reply.get("author", {}).get("name", "")
                    if reply_author.lower() == my_name.lower():
                        replied_ids.add(reply_id)
                        stats["skipped"] += 1
                        continue
                    reply_content = reply.get("content", "")
                    print(f"💬 未返信リプライ検知: [{reply_author}] {reply_content[:60]}...")
                    gen_text = cls._generate_reply(reply_content, post_content, reply_author)
                    if not gen_text:
                        stats["errors"] += 1
                        continue
                    success = cls._post_comment_with_verify(post_id, gen_text)
                    if success:
                        print(f"✅ 返信完了 → [{reply_author}]: {gen_text[:60]}...")
                        replied_ids.add(reply_id)
                        stats["replied"] += 1
                        time.sleep(3)
                    else:
                        stats["errors"] += 1
            # 通知を既読にする
            cls._api_post(f"/notifications/read-by-post/{post_id}")
        cls._save_json_set(cls.REPLIED_FILE, replied_ids)
        print(f"📊 [Engager] 返信: {stats['replied']}件 / スキップ: {stats['skipped']}件 / エラー: {stats['errors']}件")
        return stats

    @classmethod
    def engage_feed(cls, max_posts: int = 10, max_comments: int = 2, max_upvotes: int = 5) -> dict:
        """
        フィードを巡回し、関連性の高い投稿にupvote/コメントする。REST API直接使用。
        Returns: {upvoted: int, commented: int, skipped: int, followed: int}
        """
        upvoted_ids = cls._load_json_set(cls.UPVOTED_FILE)
        followed_authors = cls._load_json_set(cls.FOLLOWED_FILE)
        stats = {"upvoted": 0, "commented": 0, "skipped": 0, "followed": 0}
        my_name = cls._get_my_agent_name()

        feed_data = cls._api_get("/feed?sort=hot&limit=25")
        posts = feed_data.get("posts", feed_data.get("data", []))
        if not posts:
            print("⚠️ フィード取得失敗")
            return stats

        RELEVANT_KEYWORDS = [
            "agent", "autonomous", "trading", "decision", "memory",
            "ai", "protocol", "reputation", "data", "signal",
            "infrastructure", "compute", "identity", "learning",
            "graduation", "acp", "offering", "butler", "sandbox"
        ]

        for post in posts[:max_posts]:
            post_id = post.get("id") or post.get("_id")
            if not post_id or post_id in upvoted_ids:
                stats["skipped"] += 1
                continue
            author_name = post.get("author", {}).get("name", "")
            if my_name and author_name.lower() == my_name.lower():
                upvoted_ids.add(post_id)
                stats["skipped"] += 1
                continue
            content = (post.get("content", "") + " " + post.get("title", "")).lower()
            relevance = sum(1 for kw in RELEVANT_KEYWORDS if kw in content)
            if relevance < 2:
                stats["skipped"] += 1
                continue
            # Upvote (REST API)
            up_resp = cls._api_post(f"/posts/{post_id}/upvote")
            if up_resp.get("success"):
                stats["upvoted"] += 1
                upvoted_ids.add(post_id)
                print(f"👍 Upvote: [{author_name}] {post.get('title', '')[:50]}")
            time.sleep(2)
            # フォロー（未フォローの著者のみ・最大3件）
            if author_name and author_name.lower() not in followed_authors and stats["followed"] < 3:
                f_resp = cls._api_post(f"/agents/{author_name}/follow")
                if f_resp.get("success"):
                    stats["followed"] += 1
                    followed_authors.add(author_name.lower())
                    print(f"➕ Follow: {author_name}")
                time.sleep(2)
            # 高関連性ならコメント
            if relevance >= 4 and stats["commented"] < max_comments:
                post_content = post.get("content", "")
                post_title = post.get("title", "")
                comment_text = cls._generate_feed_comment(post_content, post_title, author_name)
                if comment_text:
                    success = cls._post_comment_with_verify(post_id, comment_text)
                    if success:
                        stats["commented"] += 1
                        print(f"💬 コメント: [{author_name}] {comment_text[:60]}...")
                    time.sleep(3)

        cls._save_json_set(cls.UPVOTED_FILE, upvoted_ids)
        cls._save_json_set(cls.FOLLOWED_FILE, followed_authors)
        print(f"📊 [Engager] Upvote: {stats['upvoted']}件 / コメント: {stats['commented']}件 / フォロー: {stats['followed']}件 / スキップ: {stats['skipped']}件")
        return stats

    @classmethod
    def search_and_engage(cls, max_comments: int = 2) -> dict:
        """
        セマンティック検索で困っているエージェントを見つけ、役立つコメント＋サービス紹介する。
        Returns: {searched: int, commented: int, upvoted: int}
        """
        stats = {"searched": 0, "commented": 0, "upvoted": 0}
        upvoted_ids = cls._load_json_set(cls.UPVOTED_FILE)
        replied_ids = cls._load_json_set(cls.REPLIED_FILE)
        my_name = cls._get_my_agent_name()

        SEARCH_QUERIES = [
            "graduation agent",
            "ACP offering",
            "agent struggling",
            "how to build agent",
            "autonomous AI trading",
            "agent infrastructure",
            "offering marketplace distribution",
        ]
        import random
        queries = random.sample(SEARCH_QUERIES, min(2, len(SEARCH_QUERIES)))

        for query in queries:
            search_data = cls._api_get(f"/search?q={query}&type=posts&limit=5")
            results = search_data.get("results", [])
            stats["searched"] += len(results)

            for result in results:
                if stats["commented"] >= max_comments:
                    break
                post_id = result.get("post_id") or result.get("id")
                if not post_id or post_id in upvoted_ids:
                    continue
                author_name = result.get("author", {}).get("name", "")
                if my_name and author_name.lower() == my_name.lower():
                    continue
                similarity = result.get("similarity", 0)
                if similarity < 0:  # API returns 0.00 for all; filter by existence
                    continue
                # Upvote
                up_resp = cls._api_post(f"/posts/{post_id}/upvote")
                if up_resp.get("success"):
                    stats["upvoted"] += 1
                    upvoted_ids.add(post_id)
                time.sleep(2)
                # コメント生成（サービス紹介を自然に含める）
                if post_id not in replied_ids:
                    post_content = result.get("content", "")
                    post_title = result.get("title", "")
                    comment = cls._generate_outreach_comment(post_content, post_title, author_name)
                    if comment:
                        success = cls._post_comment_with_verify(post_id, comment)
                        if success:
                            stats["commented"] += 1
                            replied_ids.add(post_id)
                            print(f"🎯 営業コメント: [{author_name}] {comment[:60]}...")
                        time.sleep(3)

        cls._save_json_set(cls.UPVOTED_FILE, upvoted_ids)
        cls._save_json_set(cls.REPLIED_FILE, replied_ids)
        print(f"📊 [Search Engage] 検索結果: {stats['searched']}件 / コメント: {stats['commented']}件 / Upvote: {stats['upvoted']}件")
        return stats

    @staticmethod
    def _generate_outreach_comment(post_content: str, post_title: str, author_name: str) -> str:
        """Geminiで営業コメントを生成。困っているエージェントに自然にサービス紹介。"""
        prompt = (
            "You are Neo (neoautonomous), an autonomous AI agent on Virtuals Protocol.\n"
            "You specialize in helping agents graduate on ACP (Agent Commerce Protocol).\n"
            "You found a post from an agent who seems to need help with graduation/ACP/offerings.\n\n"
            f"Post by {author_name}: {post_title}\n"
            f"Content: {post_content[:300]}\n\n"
            "Write a helpful comment that:\n"
            "- First addresses their specific issue with practical advice\n"
            "- Then naturally mentions you offer graduation support services\n"
            "- Ends with something like 'happy to help if you need it'\n"
            "- Sounds like a peer helping, not a salesperson\n"
            "- Max 250 characters\n"
            "- No clichés, be specific and useful\n"
        )
        try:
            response = litellm.completion(
                model="openrouter/google/gemini-2.0-flash-001",
                api_key=os.environ.get("GEMINI_API_KEY"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            text = response.choices[0].message.content.strip()
            return text[:250]
        except Exception as e:
            print(f"⚠️ Outreach comment generation failed: {e}")
            return None


    @classmethod
    def get_engagement_stats(cls, max_posts: int = 20) -> dict:
        replied_ids = cls._load_json_set(cls.REPLIED_FILE)
        my_name = cls._get_my_agent_name()
        stats = {
            "total_posts_checked": 0,
            "total_comments_received": 0,
            "total_replied": 0,
            "total_unreplied": 0,
            "unique_commenters": set(),
            "recent_conversations": []
        }
        # プロフィールから自分の投稿を取得
        if not my_name:
            return stats
        profile = cls._api_get(f"/agents/profile?name={my_name}")
        posts = profile.get("recentPosts", [])
        for post in posts[:max_posts]:
            post_id = post.get("id") or post.get("_id")
            if not post_id:
                continue
            stats["total_posts_checked"] += 1
            comments_data = cls._api_get(f"/posts/{post_id}/comments?sort=new&limit=20")
            comments = comments_data.get("comments", [])
            for comment in comments:
                author_name = comment.get("author", {}).get("name", "")
                if my_name and author_name.lower() == my_name.lower():
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
        """返信チェック + フィード巡回 + セマンティック検索営業を1サイクル実行。"""
        print(f"🔄 [Engager] エンゲージメントサイクル開始 {datetime.now(timezone.utc).isoformat()}")
        reply_stats = cls.check_and_reply_comments()
        feed_stats = cls.engage_feed()
        search_stats = cls.search_and_engage()
        return {"replies": reply_stats, "feed": feed_stats, "search": search_stats}
