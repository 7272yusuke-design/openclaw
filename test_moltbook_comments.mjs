import { Moltbook } from 'moltbook';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const client = new Moltbook({ apiKey: process.env.MOLTBOOK_API_KEY });

// 自分の投稿一覧を取得
const posts = await client.getPosts({ limit: 5, sort: 'new' });
console.log("=== 最新5投稿 ===");
for (const p of (posts.posts || posts || [])) {
    console.log(`\nID: ${p.id || p._id}`);
    console.log(`Title: ${p.title}`);
    console.log(`Content: ${(p.content || '').substring(0, 80)}...`);
    console.log(`Upvotes: ${p.upvotes ?? p.score ?? '?'} | Comments: ${p.commentCount ?? p.comments ?? '?'}`);
    
    // コメントがあれば取得
    const postId = p.id || p._id;
    if (postId) {
        try {
            const comments = await client.getComments(postId);
            const list = comments.comments || comments || [];
            if (list.length > 0) {
                console.log(`  --- コメント ${list.length}件 ---`);
                for (const c of list) {
                    console.log(`  [${c.author?.name || c.authorName || '?'}] ${(c.content || c.body || '').substring(0, 100)}`);
                }
            }
        } catch(e) {
            console.log(`  コメント取得エラー: ${e.message}`);
        }
    }
}
