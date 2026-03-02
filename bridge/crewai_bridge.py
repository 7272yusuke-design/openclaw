from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RiskPolicyModel(BaseModel):
    risk_appetite: str = Field(description="Conservative / Moderate / Aggressive")
    min_rating: str = Field(description="最低信用格付け (e.g., AA, A, BBB)")
    max_ltv: float = Field(description="最大LTV (Loan-to-Value) 比率 (0.0 to 1.0)")
    sector_advice: str = Field(description="セクター配分に関する具体的なアドバイス")

class StrategyInstructionModel(BaseModel):
    target_sectors: List[str] = Field(description="重点投資セクターのリスト")
    action_directive: str = Field(description="ACP Executorが実行すべき具体的な行動指針")
    arbitrage_opportunity: Optional[Dict[str, Any]] = Field(description="検知された裁定取引の機会（DEX名、期待利益率、ルート等）", default=None)
    audit_summary: str = Field(description="監査官による最終的なリスク評価と修正の要約")

class NeoStrategicPlan(BaseModel):
    status: str = Field(default="success", description="success または failed")
    risk_policy: RiskPolicyModel = Field(description="確定版リスクポリシー")
    strategy: StrategyInstructionModel = Field(description="監査済みの具体的戦略")
    virtuals_payload: Optional[Dict[str, Any]] = Field(description="Virtuals Protocol(ACP)へ送信するためのJSONデータ案")

class CrewResult(BaseModel):
    # 後方互換性のために残す（または必要に応じて移行）
    status: str = Field(description="success または failed")
    summary: str = Field(description="実行したタスクの簡潔な要約（200文字以内）")
    virtuals_payload: Optional[Dict[str, Any]] = Field(description="Virtuals Protocol(ACP)へ送信するためのJSONデータ")
    next_action_suggestion: str = Field(description="OpenClawが次に取るべき行動の提案")
