from pydantic import BaseModel, Field, validator
from typing import Literal

class CreditProfile(BaseModel):
    repayment_history: float = Field(..., ge=0, le=100, description="返済実績 (30%)")
    collateral_value: float = Field(..., ge=0, le=100, description="担保価値 (20%)")
    external_data: float = Field(..., ge=0, le=100, description="外部データ (15%)")
    community_rating: float = Field(..., ge=0, le=100, description="コミュニティ評価 (15%)")
    transaction_completion: float = Field(..., ge=0, le=100, description="取引完遂率 (10%)")
    activity_level: float = Field(..., ge=0, le=100, description="活動量 (10%)")

class CreditScoreResult(BaseModel):
    total_score: float = Field(..., ge=0, le=100, description="総合信用スコア")
    rating: Literal["AAA", "AA", "A", "BBB", "BB", "B"] = Field(..., description="信用格付け")

class CreditScoreCalculator:
    """
    エージェントの信用スコアを計算するクラス。
    """
    @staticmethod
    def calculate(profile: CreditProfile) -> CreditScoreResult:
        score = (
            (profile.repayment_history * 0.3) +
            (profile.collateral_value * 0.2) +
            (profile.external_data * 0.15) +
            (profile.community_rating * 0.15) +
            (profile.transaction_completion * 0.1) +
            (profile.activity_level * 0.1)
        )
        score = round(score, 2)

        if score >= 90: rating = "AAA"
        elif score >= 80: rating = "AA"
        elif score >= 70: rating = "A"
        elif score >= 60: rating = "BBB"
        elif score >= 50: rating = "BB"
        else: rating = "B"

        return CreditScoreResult(total_score=score, rating=rating)

if __name__ == "__main__":
    # テスト実行
    test_profile = CreditProfile(
        repayment_history=95,    # 非常に良い
        collateral_value=80,     # 高い
        external_data=70,        # 標準以上
        community_rating=85,     # 高評価
        transaction_completion=90, # ほぼ完遂
        activity_level=60        # 標準
    )
    result = CreditScoreCalculator.calculate(test_profile)
    print(f"Credit Score: {result.total_score}, Rating: {result.rating}")
