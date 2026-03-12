#!/usr/bin/env node

import { Moltbook } from 'moltbook';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// .env の場所を確実に指定
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '.env') });

const [,, cmd, ...args] = process.argv;

if (cmd === 'post') {
    const text = args.join(' ');
    // APIキーがない場合は警告
    if (!process.env.MOLTBOOK_API_KEY) {
        console.error("❌ エラー: .env 内に MOLTBOOK_API_KEY が見つかりません。");
        process.exit(1);
    }

    const client = new Moltbook({
        apiKey: process.env.MOLTBOOK_API_KEY
    });

    client.post(text)
        .then(() => {
            console.log("✅ Moltbookへの投稿に成功しました");
            process.exit(0);
        })
        .catch(err => {
            console.error("❌ 投稿エラー:", err.message);
            process.exit(1);
        });
} else {
    console.log("Usage: moltbook post <text>");
    process.exit(1);
}
