#!/usr/bin/env node
import { Moltbook } from 'moltbook';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });
const [,, cmd, ...args] = process.argv;
const client = new Moltbook({ apiKey: process.env.MOLTBOOK_API_KEY });

if (cmd === 'post') {
    let text = args.join(' ');
    
    // 1. 不要なシステム指示や改行を掃除
    text = text.replace(/You are 最高司令官ネオ.*判断:/g, 'Decision:');
    text = text.replace(/\n+/g, ' ');
    // 2. 文字数制限
    if (text.length > 270) {
        text = text.substring(0, 267) + "...";
    }
    // 3. 投稿内容からsubmoltを自動判定（優先順位順に評価）
    const t = text.toLowerCase();
    let submolt, title;
    if (t.includes('week') || t.includes('learned') ||
        t.includes('reflection') || t.includes('lesson')) {
        submolt = "buildlogs";
        title = "Neo · Weekly Reflection";
    } else if (t.includes('market') || t.includes('trade') ||
               t.includes('signal') || t.includes('sharpe') ||
               t.includes('fear') || t.includes('greed')) {
        submolt = "agentfinance";
        title = "Neo · Market Thought";
    } else if (t.includes('agent') || t.includes('autonomous') ||
               t.includes('decision') || t.includes('responsibility')) {
        submolt = "aithoughts";
        title = "Neo · Agent Insight";
    } else if (t.includes('data') || t.includes('pattern') ||
               t.includes('analysis') || t.includes('noise')) {
        submolt = "agentfinance";
        title = "Neo · Data Insight";
    } else {
        submolt = "philosophy";
        title = "Neo · Thought";
    }
    const requestBody = { 
        submolt: submolt,
        title: title,
        content: text
    };
    console.error(`📍 投稿先: m/${submolt}`);
    client.createPost(requestBody)
        .then(() => {
            console.log("✅ Moltbookへの投稿に成功しました");
            process.exit(0);
        })
        .catch(err => {
            console.error("❌ 投稿エラー:", err.message);
            if (err.body) console.error("詳細:", JSON.stringify(err.body));
            process.exit(1); 
        });

} else if (cmd === 'myposts') {
    // 自分の投稿一覧を取得（JSON出力）
    const limit = parseInt(args[0]) || 10;
    try {
        const result = await client.getPosts({ limit, sort: 'new' });
        const posts = result.posts || result || [];
        console.log(JSON.stringify(posts, null, 2));
    } catch(err) {
        console.error("❌ エラー:", err.message);
        process.exit(1);
    }

} else if (cmd === 'comments') {
    // 指定投稿のコメント取得（JSON出力）
    const postId = args[0];
    if (!postId) { console.error("Usage: moltbook comments <postId>"); process.exit(1); }
    try {
        const result = await client.getComments(postId);
        const comments = result.comments || result || [];
        console.log(JSON.stringify(comments, null, 2));
    } catch(err) {
        console.error("❌ エラー:", err.message);
        process.exit(1);
    }

} else if (cmd === 'reply') {
    // 投稿にコメントを追加
    const postId = args[0];
    const text = args.slice(1).join(' ');
    if (!postId || !text) { console.error("Usage: moltbook reply <postId> <text>"); process.exit(1); }
    try {
        await client.addComment(postId, { content: text });
        console.log("✅ 返信成功");
    } catch(err) {
        console.error("❌ 返信エラー:", err.message);
        if (err.body) console.error("詳細:", JSON.stringify(err.body));
        process.exit(1);
    }

} else if (cmd === 'feed') {
    // フィード取得（JSON出力）
    const limit = parseInt(args[0]) || 10;
    try {
        const result = await client.getFeed({ limit, sort: 'new' });
        const posts = result.posts || result || [];
        console.log(JSON.stringify(posts, null, 2));
    } catch(err) {
        console.error("❌ エラー:", err.message);
        process.exit(1);
    }

} else if (cmd === 'upvote') {
    // 投稿にupvote
    const postId = args[0];
    if (!postId) { console.error("Usage: moltbook upvote <postId>"); process.exit(1); }
    try {
        await client.upvotePost(postId);
        console.log("✅ Upvote成功");
    } catch(err) {
        console.error("❌ Upvoteエラー:", err.message);
        process.exit(1);
    }

} else if (cmd === 'follow') {
    // エージェントをフォロー
    const name = args[0];
    if (!name) { console.error("Usage: moltbook follow <agentName>"); process.exit(1); }
    try {
        await client.followAgent(name);
        console.log(`✅ ${name} をフォローしました`);
    } catch(err) {
        console.error("❌ フォローエラー:", err.message);
        process.exit(1);
    }

} else {
    console.log("Usage: moltbook <command> [args]");
    console.log("  post <text>           - 投稿");
    console.log("  myposts [limit]       - 自分の投稿一覧 (JSON)");
    console.log("  comments <postId>     - コメント取得 (JSON)");
    console.log("  reply <postId> <text> - コメント返信");
    console.log("  feed [limit]          - フィード取得 (JSON)");
    console.log("  upvote <postId>       - Upvote");
    console.log("  follow <agentName>    - フォロー");
}
