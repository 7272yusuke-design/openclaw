import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, ValidationError
from core.memory_db import NeoMemoryDB

logger = logging.getLogger(__name__)

# --- Schema Definitions v5.1 (Diplomatic Intelligence Extension) ---

class InteractionEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    action: str
    reaction_score: float = Field(..., ge=-1.0, le=1.0)
    summary: str

class TargetAgentIntel(BaseModel):
    agent_name: str
    strategic_asset: str
    vulnerability: str
    influence_score: float = Field(..., ge=0.0, le=1.0)
    behavioral_dna: str
    negotiation_hook: str
    synergy_potential: float = Field(..., ge=0.0, le=1.0)
    trust_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    intel_exchange_status: str = Field(default="L1", pattern="^L[1-3]$")
    interaction_history: List[InteractionEvent] = Field(default_factory=list)
    status: str = "IDENTIFIED"

    def recalculate_trust(self, response_quality: float, alpha: float = 0.1, time_passed_hours: float = 0, beta: float = 0.01):
        new_trust = self.trust_score + (response_quality * alpha) - (time_passed_hours * beta)
        self.trust_score = max(-1.0, min(1.0, new_trust))
        return self.trust_score

class MarketIntel(BaseModel):
    price: float
    price_24h_avg: float
    social_velocity: float = Field(..., ge=0.0)
    whale_alert: str
    current_liquidity: Dict[str, float] = Field(default_factory=dict)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class StrategicIntel(BaseModel):
    expected_pnet: float
    risk_mitigation_plan: str
    success_probability: float = Field(..., ge=0.0, le=1.0)
    strategy_id: str
    diplomatic_presets: Dict[str, str] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ExecutionFeedback(BaseModel):
    actual_slippage: float
    actual_gas: float
    latency_ms: int
    execution_status: str
    tx_hash: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BlackboardSchemaV5_1(BaseModel):
    market_intel: Dict[str, MarketIntel] = Field(default_factory=dict)
    strategic_intel: Optional[StrategicIntel] = None
    diplomacy_intel: Dict[str, TargetAgentIntel] = Field(default_factory=dict)
    execution_history: List[ExecutionFeedback] = Field(default_factory=list)
    system_status: str = "ONLINE"
    version: str = "5.1"

# --- Blackboard Manager ---

class NeoBlackboard:
    FILE_PATH = "vault/blackboard/live_intel.json"
    # 長期記憶エンジンをクラス変数として保持
    _memory = NeoMemoryDB()

    @classmethod
    def load(cls) -> Dict[str, Any]:
        if not os.path.exists(cls.FILE_PATH):
            return BlackboardSchemaV5_1().model_dump()
        try:
            with open(cls.FILE_PATH, "r") as f:
                data = json.load(f)
                BlackboardSchemaV5_1(**data)
                return data
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Blackboard Schema Validation Failed (v5.1): {e}")
            return BlackboardSchemaV5_1().model_dump()

    @classmethod
    def update(cls, section: str, data: Any):
        current_intel = cls.load()
        try:
            # 既存のロジック (変更なし)
            if section == "market_intel":
                for token, val in data.items():
                    current_intel["market_intel"][token] = MarketIntel(**val).model_dump()
            elif section == "strategic_intel":
                current_intel["strategic_intel"] = StrategicIntel(**data).model_dump()
            elif section == "diplomacy_intel":
                for agent, val in data.items():
                    current_intel["diplomacy_intel"][agent] = TargetAgentIntel(**val).model_dump()
            elif section == "execution_feedback":
                feedback = ExecutionFeedback(**data)
                current_intel.setdefault("execution_history", []).append(feedback.model_dump())
                if len(current_intel["execution_history"]) > 100:
                    current_intel["execution_history"].pop(0)
            
            current_intel["version"] = "5.1"
            
            # 保存
            with open(cls.FILE_PATH, "w") as f:
                json.dump(current_intel, f, indent=2, ensure_ascii=False)
            
            # --- ここから長期記憶への自動同期 ---
            memory_content = f"Update to {section}: {json.dumps(data, ensure_ascii=False)}"
            cls._memory.store(
                content=memory_content,
                metadata={"section": section, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            # ----------------------------------
            
            logger.info(f"Blackboard section '{section}' updated and synced to ChromaDB.")
        except ValidationError as e:
            logger.error(f"Update rejected (v5.1) in section '{section}': {e}")
            raise
