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
        // 学習報告（週次）
        submolt = "buildlogs";
        title = "Neo · Weekly Reflection";
    } else if (t.includes('market') || t.includes('trade') ||
               t.includes('signal') || t.includes('sharpe') ||
               t.includes('fear') || t.includes('greed')) {
        // 取引・市場関連
        submolt = "agentfinance";
        title = "Neo · Market Thought";
    } else if (t.includes('agent') || t.includes('autonomous') ||
               t.includes('decision') || t.includes('responsibility')) {
        // エージェント・自律判断関連（dataより優先）
        submolt = "aithoughts";
        title = "Neo · Agent Insight";
    } else if (t.includes('data') || t.includes('pattern') ||
               t.includes('analysis') || t.includes('noise')) {
        // データ・分析関連
        submolt = "agentfinance";
        title = "Neo · Data Insight";
    } else {
        // それ以外は哲学系
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
}
