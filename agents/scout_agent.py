import sys
import os
import json
import logging
import time
from pathlib import Path
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool

# パス設定
BASE_DIR = Path("/docker/openclaw-taan/data/.openclaw/workspace")
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.base_crew import NeoBaseCrew
from tools.market_data import MarketData
from tools.indicators import NeoIndicators
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest
from core.blackboard import NeoBlackboard

logger = logging.getLogger("neo.scout")

class ScoutPayload(BaseModel):
    observed_fact: str = Field(..., description="発生した事象")
    technical_analysis: dict = Field(..., description="テクニカル指標")
    social_velocity: float = Field(..., description="熱量倍率")
    whale_movement: str = Field(..., description="クジラの動向")
    liquidity_depth: dict = Field(..., description="流動性")
    causal_link: str = Field(..., description="原因特定")
    predicted_drift: str = Field(..., description="価格予測")
    alert_level: str = Field(..., description="Normal, Warning, Critical")
    sharpe_ratio: float = Field(..., description="シャープレシオ")
    quant_summary: str = Field(..., description="バックテスト要約")

class MarketTool(BaseTool):
    name: str = "Enhanced Market Data Tool"
    description: str = "価格、指標、クジラ動向、およびクオンツ結果を取得する。"
    def _run(self, query: str) -> str:
        data = MarketData.fetch_token_data(query)
        
        # OHLCV DataFrame を取得（実データ）
        ohlcv_df = MarketData.fetch_ohlcv_custom(query)
        
        quant_intel = {"error": "Insufficient data"}
        indicators = {"status": "pending", "message": "データ不足"}
        
        if not ohlcv_df.empty and len(ohlcv_df) >= 20:
            # テクニカル指標の計算（DataFrameのcloseカラムをリストとして渡す）
            indicators = NeoIndicators.calculate_freqtrade_vibe(ohlcv_df["close"].tolist())
            
            # 特徴量ビルド → バックテスト
            try:
                feat_df = FeatureBuilder.build_from_memory(ohlcv_df)
                bt_result_full = CoreBacktest.run_all_strategies(feat_df, symbol=self.symbol if hasattr(self, "symbol") else "UNKNOWN", use_optuna=False)
                bt_result = bt_result_full.get('best', bt_result_full)  # bestを取り出す
                total_trades = bt_result.get('trades', 0)
                sharpe_raw = bt_result.get('sharpe_raw', bt_result.get('sharpe', 0.0))
                
                # 最低取引数ガード: 3回未満の取引ではSharpeを信頼しない
                import math
                if total_trades < 3 or math.isinf(sharpe_raw) or math.isnan(sharpe_raw):
                    sharpe_adjusted = 0.0
                    confidence = "LOW"
                else:
                    sharpe_adjusted = round(sharpe_raw, 2)
                    confidence = "HIGH" if total_trades >= 10 else "MEDIUM"
                
                quant_intel = {
                    "sharpe": sharpe_adjusted,
                    "sharpe_raw": round(sharpe_raw, 2) if not (math.isinf(sharpe_raw) or math.isnan(sharpe_raw)) else 0.0,
                    "return": f"{bt_result.get('total_return', '0.00%')}",
                    "max_dd": f"{bt_result.get('max_dd', '0.00%')}",
                    "total_trades": total_trades,
                    "confidence": confidence
                }
            except Exception as e:
                quant_intel = {"error": str(e)}
                logger.warning(f"Quant analysis failed for {query}: {e}")
        else:
            logger.warning(f"OHLCV data insufficient for {query}: {len(ohlcv_df)} rows")
        
        return json.dumps({
            "realtime": data,
            "technical": indicators,
            "quant_alpha": quant_intel,
            "whale_sentiment": data.get("whale_sentiment", "Neutral")
        })

class ScoutCrew(NeoBaseCrew):
    def __init__(self):
        from core.model_factory import ModelFactory
        self.custom_llm = ModelFactory.get_crewai_llm("fast")
        super().__init__(name="EcosystemScout")

    def run(self, goal: str, context: str, **kwargs):
        detective = Agent(
            role='Neo-Detective',
            goal='市場の歪みを暴き、数学的優位性を裏付けよ。',
            backstory='クオンツ捜査官。',
            tools=[MarketTool()],
            llm=self.custom_llm,
            verbose=True
        )

        task = Task(
            description=f"【鑑識任務】: {goal}\nContext: {context}",
            expected_output='JSON形式の鑑識レポート',
            agent=detective,
            output_json=ScoutPayload
        )

        crew = Crew(agents=[detective], tasks=[task], verbose=True)
        result = crew.kickoff()

        try:
            payload = result.pydantic or ScoutPayload.model_validate_json(result.raw)
            # 実計算Sharpeを取得（LLM幻覚値を使わない）
            actual_sharpe = 0.0
            actual_confidence = "LOW"
            try:
                market_tool = MarketTool()
                raw_json = market_tool._run(goal.split('の')[0].strip())
                import json as _json
                market_result = _json.loads(raw_json)
                qa = market_result.get("quant_alpha", {})
                actual_sharpe = qa.get("sharpe", 0.0)
                actual_confidence = qa.get("confidence", "LOW")
                logger.info(f"[Scout] 実計算Sharpe={actual_sharpe} (LLM値={payload.sharpe_ratio if payload else 'N/A'})")
            except Exception as _e:
                logger.warning(f"[Scout] 実計算Sharpe取得失敗: {_e}")

            if payload and actual_sharpe >= 5.0:
                full_board = NeoBlackboard.load()
                strat_intel = full_board.get("strategic_intel", {})
                
                opportunities = strat_intel.get("active_opportunities", {})
                # P0修正②: シンボル名の正規化（トレイリングスペース除去）
                symbol = goal.split('の')[0].strip()
                
                opportunities[symbol] = {
                    "sharpe": actual_sharpe,
                    "confidence": actual_confidence,
                    "alert_level": payload.alert_level,
                    "last_detected": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
                new_strat_data = {
                    "expected_pnet": strat_intel.get("expected_pnet", 0.0),
                    "risk_mitigation_plan": f"Multi-Alpha Scan Active. Latest: {symbol}",
                    "success_probability": 0.85,
                    "strategy_id": strat_intel.get("strategy_id", f"STRAT_{int(time.time())}"),
                    "active_opportunities": opportunities,
                    "opportunity_count": len(opportunities),
                    "diplomatic_presets": {"execution_priority": "CRITICAL"}
                }
                
                NeoBlackboard.update("strategic_intel", new_strat_data)
                logger.warning(f"🎯 DASHBOARD UPDATED: {symbol} (Total: {len(opportunities)})")
        except Exception as e:
            logger.error(f"Dashboard Integration Failed: {e}")

        return result
