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
    
    // 1. 不要なシステム指示（You are...）や改行を掃除
    text = text.replace(/You are 最高司令官ネオ.*判断:/g, 'Decision:'); // システムプロンプト混入をカット
    text = text.replace(/\n+/g, ' '); // 改行をスペースに置換（APIエラー対策）

    // 2. 文字数制限の厳格化（400エラーの主因）
    // 安全のため、Moltbookの標準的な制限である280文字に収めます
    if (text.length > 270) {
        text = text.substring(0, 267) + "...";
    }

    const requestBody = { 
        submolt: "all", 
        title: "Neo Trinity Council",
        content: text
    };

    client.createPost(requestBody)
        .then(() => {
            console.log("✅ Moltbookへの投稿に成功しました");
            process.exit(0);
        })
        .catch(err => {
            console.error("❌ 投稿エラー:", err.message);
            // 失敗理由をログに残す
            if (err.body) console.error("詳細:", JSON.stringify(err.body));
            process.exit(1); 
        });
}
