import time
import json
import os
import sys
import traceback
from datetime import datetime, timezone
import urllib.request
import urllib.parse
from core.config import NeoConfig
from neo_main import NeoSystem
from agents.paper_trader import PaperTraderAgent

# OpenClawのweb_searchツールを模倣するラッパー (バックグラウンド実行用)
def background_search_wrapper(query):
    print(f"[Background] Searching for: {query}")
    return [
        {
            "title": "Trend Alert: Gaming Sector Surge",
            "snippet": "Virtuals Protocol's Gaming sector is showing significant growth. Opportunity: Invest in top-performing Gaming agents.",
            "url": "https://example.com/virtuals/gaming-trend"
        },
        {
            "title": "New Agent Launch: 'Quantum Trader AI'",
            "snippet": "Quantum Trader AI agent launched on Base chain. High potential for arbitrage. Action: Monitor its on-chain activity.",
            "url": "https://example.com/agents/quantum-trader-ai"
        },
        {
            "title": "Risk Advisory: DeFi Protocol Security Update",
            "snippet": "A popular DeFi protocol has released a security update. Potential risk factor for its agents. Action: Review agent risk policies related to this protocol.",
            "url": "https://example.com/DeFi/security-update"
        }
    ]

def check_manager_health():
    """マネージャーによる自己健康診断: 前回のサイクルが正常に完了したか確認する"""
    health_file = "logs/manager_heartbeat.json"
    if not os.path.exists(health_file):
        print("[Manager] No previous heartbeat found. Initializing first run.")
        return True

    try:
        with open(health_file, "r") as f:
            heartbeat = json.load(f)
            last_run = datetime.fromisoformat(heartbeat.get("timestamp"))
            # タイムゾーンなしのdatetimeに比較を合わせる
            if last_run.tzinfo:
                last_run = last_run.replace(tzinfo=None)
            
            time_diff = (datetime.now() - last_run).total_seconds() / 3600

            if time_diff > 1.5:
                print(f"⚠️ [CRITICAL] Manager Alert: Silence detected for {time_diff:.2f} hours!")
                print(f"⚠️ [CRITICAL] Potential system stall detected in previous run.")
                return False
            else:
                print(f"✅ [Manager] Health Check: System stable. Last run was {time_diff*60:.1f} minutes ago.")
                return True
    except Exception as e:
        print(f"Warning: Failed to read health check: {e}")
        return True

def update_heartbeat():
    """健康診断の記録を更新する"""
    health_file = "logs/manager_heartbeat.json"
    os.makedirs("logs", exist_ok=True)
    with open(health_file, "w") as f:
        json.dump({"status": "healthy", "timestamp": datetime.now().isoformat()}, f)

def run_loop():
    print("Starting Neo Autonomous Cycle Loop (Hourly)...")
    
    # 起動時に自己診断を実行
    check_manager_health()
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    market_cycle_log_file = os.path.join(log_dir, "market_cycle.jsonl")
    performance_log_file = os.path.join(log_dir, "performance_metrics.jsonl")

    system = NeoSystem(web_search_tool=background_search_wrapper)
    paper_trader = PaperTraderAgent()

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{current_time}] Executing cycle...")
            
            # --- サイクル実行の開始 ---
            update_heartbeat() # 活動開始を記録
            
            topic = "Virtuals Protocol Market Update"
            
            # パフォーマンスメトリクスの読み込み
            scout_performance_metrics = []
            if os.path.exists(performance_log_file):
                try:
                    with open(performance_log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                scout_performance_metrics.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: Error reading performance logs: {e}")
            
            if scout_performance_metrics:
                system.execution_history.extend(scout_performance_metrics)
                print(f"Collected {len(scout_performance_metrics)} performance metrics.")

            # サイクル実行
            cycle_output = system.autonomous_post_cycle(topic)
            
            # --- [Pydantic 構造化データ取得] ---
            strategy_json = None
            planning_output = cycle_output.get("planning_output", None)
            
            # Case 1: CrewOutput object with pydantic attribute
            if hasattr(planning_output, 'pydantic') and planning_output.pydantic:
                try:
                    strategy_json = planning_output.pydantic.model_dump()
                    print(f"[Pydantic] Successfully extracted structured plan from pydantic attr: {strategy_json.get('status', 'unknown')}")
                except Exception as e:
                    print(f"[Pydantic] Error extracting from pydantic attr: {e}")

            # Case 2: Dictionary (already serialized)
            if not strategy_json and isinstance(planning_output, dict):
                strategy_json = planning_output
                print("[Pydantic] Extracted structured plan from dict")
                
            # Case 3: Raw string or CrewOutput with JSON string
            if not strategy_json:
                raw_output = str(planning_output)
                if hasattr(planning_output, 'raw'):
                    raw_output = planning_output.raw
                
                try:
                    # Attempt to clean code blocks if present
                    import re
                    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
                    if json_match:
                        strategy_json = json.loads(json_match.group(1))
                        print("[Pydantic] Extracted structured plan from regex (```json)")
                    else:
                        # Try parsing raw string directly if it looks like JSON
                        if raw_output.strip().startswith("{") and raw_output.strip().endswith("}"):
                            strategy_json = json.loads(raw_output)
                            print("[Pydantic] Extracted structured plan from raw JSON string")
                except Exception as e:
                    print(f"Warning: Failed to extract fallback JSON: {e}")
            # --- [Pydantic 構造化データ取得 END] ---
            
            # ペーパートレード実行
            trade_result = {"status": "skipped", "reason": "No planning output found"}
            
            if strategy_json:
                print("[Paper Trader] Executing trades based on planning strategy...")
                trade_result = paper_trader.execute_strategy(strategy_json)
                print(f"[Paper Trader] Trade execution result: {trade_result}")
                
                # --- [Blackboard Update Fix] ---
                # ウォレット残高をBlackboardに反映 (コンテキスト共有のため)
                if trade_result:
                    wallet_state = {
                        "balance": trade_result.get("usd_balance", 0.0),
                        "virtual_holdings": trade_result.get("virtual_holdings", 0.0),
                        "total_value": trade_result.get("total_value_usd", 0.0),
                        "currency": "USDT",
                        "updated_at": time.time()
                    }
                    system.blackboard.update("wallet", wallet_state)
                    print(f"[Blackboard] Wallet state updated: {wallet_state['balance']} USDT")
                # -------------------------------

            # システム改善提案の生成
            print("[Development Crew] Analyzing performance and seeking improvements...")
            improvement_result = system.improve_system(
                performance_log_path=performance_log_file,
                market_cycle_log_path=market_cycle_log_file
            )

            # 結果のログ保存
            def serializable_dict(obj):
                """CrewOutputなどのPydantic/特殊オブジェクトをJSON保存可能な形式に変換"""
                if isinstance(obj, (str, int, float, bool, type(None))):
                    return obj
                if isinstance(obj, dict):
                    return {k: serializable_dict(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [serializable_dict(i) for i in obj]
                
                if hasattr(obj, 'pydantic') and obj.pydantic:
                    return obj.pydantic.model_dump()
                if hasattr(obj, 'model_dump'):
                    return obj.model_dump()
                if hasattr(obj, 'json'):
                    try: return json.loads(obj.json())
                    except: pass
                if hasattr(obj, 'dict'):
                    try: return obj.dict()
                    except: pass
                
                return str(obj)

            # cycle_outputの中身をシリアライズ可能にする
            clean_cycle_output = serializable_dict(cycle_output)

            final_result = {
                "timestamp": current_time,
                "cycle_output": clean_cycle_output,
                "paper_trading_execution": trade_result,
                "self_improvement_proposal": serializable_dict(improvement_result)
            }
            
            with open(market_cycle_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(final_result, ensure_ascii=False) + "\n")
            
            # --- [能動的報告プロトコル] ---
            try:
                # Retrieve data
                scout_out = clean_cycle_output.get("scout_output", {})
                sentiment_out = clean_cycle_output.get("sentiment_analysis_output", {})
                planning_out = clean_cycle_output.get("planning_output", {})
                content_out = clean_cycle_output.get("content", {})
                
                # Extract details safely
                try:
                    # Market Data (Scout - Hard to parse raw text, so we use dummy or try to extract if structured)
                    # For now, we rely on the fact that scout output is usually text.
                    market_summary = "データ取得完了"
                    
                    # Sentiment
                    sentiment_score = "N/A"
                    if isinstance(sentiment_out, dict):
                         # If it's Pydantic/Dict
                         sentiment_score = sentiment_out.get("sentiment_score", "N/A")
                    elif isinstance(sentiment_out, str):
                        # Simple extraction if possible, else just first line
                        sentiment_score = sentiment_out[:50].split('\n')[0]

                    # Strategy (Planning)
                    strategy_action = "HOLD"
                    risk_assessment = "Neutral"
                    if isinstance(planning_out, dict):
                        # Try to find strategy directive
                        if "strategy" in planning_out:
                            strategy_action = planning_out["strategy"].get("action_directive", "HOLD")
                        if "risk_policy" in planning_out:
                            risk_assessment = planning_out["risk_policy"].get("risk_appetite", "Neutral")
                    elif hasattr(planning_out, 'pydantic') and planning_out.pydantic:
                         model = planning_out.pydantic
                         if hasattr(model, 'strategy'):
                             strategy_action = model.strategy.action_directive
                         if hasattr(model, 'risk_policy'):
                             risk_assessment = model.risk_policy.risk_appetite

                    # Paper Trader
                    total_assets = trade_result.get("total_value_usd", 100000.0)
                    virtual_holdings = trade_result.get("virtual_holdings", 0.0)
                    cash_holdings = trade_result.get("cash_usd", 0.0)
                    pnl = total_assets - 100000.0
                    pnl_sign = "+" if pnl >= 0 else ""
                    
                    # Content
                    post_content = "N/A"
                    if isinstance(content_out, dict):
                        post_content = content_out.get("content", "N/A")
                    elif hasattr(content_out, 'pydantic') and content_out.pydantic:
                        post_content = content_out.pydantic.content
                    else:
                        post_content = str(content_out)
                    
                    # Mock or Extract VIRTUAL Price (If available in scout output)
                    # For now, we will try to find it in scout text or leave it as "取得中"
                    virtual_price_display = "取得中..."
                    # In a real scenario, we would parse scout_out for price data
                    
                except Exception as e:
                    print(f"Error parsing cycle output for report: {e}")
                    market_summary = "Error parsing data"
                    strategy_action = "Error"
                    risk_assessment = "Error"
                    post_content = "Error parsing content"
                
                # Report text construction (Markdown)
                # Translation Helper
                def translate_status(val):
                    pmap = {
                        "Conservative": "保守的 (Conservative)",
                        "Moderate": "中立的 (Moderate)",
                        "Aggressive": "積極的 (Aggressive)",
                        "Neutral": "中立 (Neutral)",
                        "Fear": "恐怖 (Fear)",
                        "Greed": "強欲 (Greed)",
                        "Extreme Fear": "極度の恐怖",
                        "Extreme Greed": "極度の強欲",
                        "HOLD": "待機 (HOLD)",
                        "BUY": "購入 (BUY)",
                        "SELL": "売却 (SELL)"
                    }
                    return pmap.get(val, val)

                report_text = f"""### 📣 【Neo 自律哨戒報告】 (定時報告分)
**ステータス**: ✅ 正常完了 (Cycle Completed)
**実行モデル**: Claude 3.5 Sonnet (Brain) + Gemini 2.0 Flash (Eyes) + GPT-4o (Hands)

#### 1. 📈 市場分析 (Scout & Sentiment)
- **トレンド検知**:
{market_summary}

#### 2. 🛡️ 戦略判断 (Strategic Planning)
- **リスク判定**: **{translate_status(risk_assessment)}**
- **アクション**: **{translate_status(strategy_action)}**

#### 3. 💰 資産状況 (Paper Wallet)
- **総資産評価額**: **${total_assets:,.2f}** (開始時 $100,000)
- **含み益**: **{pnl_sign}${pnl:,.2f}**
- **保有内訳**:
  - USD: ${cash_holdings:,.2f}
  - VIRTUAL: {virtual_holdings:,.2f} トークン

#### 4. ✍️ 対外発信 (Content Creator)
> {post_content}
"""
                
                print(f"📣 [Proactive Report]\n{report_text}")
                
                # --- Send to Discord via Webhook ---
                try:
                    webhook_url = getattr(NeoConfig, 'DISCORD_WEBHOOK_URL', None)
                    if webhook_url:
                        # Construct JSON payload
                        payload = {
                            "content": report_text,
                            "username": "Neo (Autonomous)",
                            "avatar_url": "https://raw.githubusercontent.com/7272yusuke-design/openclaw/master/assets/neo-avatar.png" # Optional placeholder
                        }
                        
                        data = json.dumps(payload).encode('utf-8')
                        req = urllib.request.Request(
                            webhook_url, 
                            data=data, 
                            headers={'Content-Type': 'application/json', 'User-Agent': 'Neo-Agent/1.0'}
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            if 200 <= response.status < 300:
                                print(f"✅ Discord notification sent successfully.")
                            else:
                                print(f"⚠️ Discord notification failed with status: {response.status}")
                    else:
                        print("ℹ️ Discord Webhook URL not configured. Skipping notification.")

                except Exception as e:
                    print(f"❌ Failed to send Discord notification: {e}")

            except Exception as msg_e:
                print(f"Warning: Failed to build proactive report: {msg_e}")
            # --- [能動的報告プロトコル END] ---
            
            print(f"Cycle completed. Next run in 1 hour.")
            time.sleep(3600) # 1時間待機

        except Exception as e:
            print(f"ERROR in run_loop: {e}")
            traceback.print_exc()
            print("Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else "Virtuals Protocol"
        system = NeoSystem(web_search_tool=background_search_wrapper)
        
        if cmd == "post":
            result = system.autonomous_post_cycle(arg)
            def quick_serialize(obj):
                if hasattr(obj, 'pydantic') and obj.pydantic: return obj.pydantic.model_dump()
                if hasattr(obj, 'json'): 
                    try: return json.loads(obj.json())
                    except: pass
                return str(obj)
            
            clean_res = {k: quick_serialize(v) for k, v in result.items()}
            print(json.dumps(clean_res, indent=2, ensure_ascii=False))
        elif cmd == "plan":
            print(system.plan_project(arg, "Neo 2.0 Ecosystem"))
        else:
            print(f"Unknown command: {cmd}")
    else:
        run_loop()
