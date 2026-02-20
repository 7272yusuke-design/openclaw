---
name: content-analyzer
description: 投稿やリサーチ結果のテキストコンテンツを受け取り、感情分析とキーワード抽出を実行します。これにより、コンテンツのトーン把握、主要キーワードの特定、読者への効果的な伝達を支援します。ニュース要約、リサーチ報告、マーケティングコンテンツなどの分析に活用できます。
---

# Content Analyzer

## Overview

このスキルは、与えられたテキストコンテンツを分析し、その感情傾向と主要なキーワードを抽出することで、より質の高い投稿や報告書の作成を支援します。

## Capabilities

### 1. 感情分析 (Sentiment Analysis)

テキストコンテンツが全体としてポジティブ、ネガティブ、ニュートラルのどの感情傾向にあるかを分析します。

*   **使用方法:**
    `python scripts/sentiment_analysis.py "<分析したいテキスト>"`
*   **出力例:**
    `Sentiment Score: {'neg': 0.0, 'neu': 0.5, 'pos': 0.5, 'compound': 0.8}`
    `Overall Sentiment: Positive`

### 2. キーワード抽出 (Keyword Extraction)

テキストコンテンツの中から重要なキーワードやフレーズを抽出し、その投稿の主要なテーマを明確にします。

*   **使用方法:**
    `python scripts/keyword_extraction.py "<分析したいテキスト>"`
*   **出力例:**
    `Keywords: ['AI', 'エージェント', '学習', '効率', '最適化']`

## Usage Examples

### リサーチ報告書の分析

ユーザー: 「このリサーチ報告書の感情傾向と主要キーワードを教えてください: 'AIエージェントの自律性向上に関する最新の研究では、画期的な進歩が見られ、その効率性と応用範囲の拡大に大きな期待が寄せられています。しかし、倫理的側面や安全性への配慮も不可欠です。'」

Bot (私):
1. `python scripts/sentiment_analysis.py "AIエージェントの自律性向上に関する最新の研究では、画期的な進歩が見られ、その効率性と応用範囲の拡大に大きな期待が寄せられています。しかし、倫理的側面や安全性への配慮も不可欠です。"`
2. `python scripts/keyword_extraction.py "AIエージェントの自律性向上に関する最新の研究では、画期的な進歩が見られ、その効率性と応用範囲の拡大に大きな期待が寄せられています。しかし、倫理的側面や安全性への配慮も不可欠です。"`

---

## Resources

### scripts/

Executable code (Python) for performing sentiment analysis and keyword extraction.

*   `sentiment_analysis.py`: テキストの感情分析を行うスクリプト。
*   `keyword_extraction.py`: テキストからキーワードを抽出するスクリプト。
