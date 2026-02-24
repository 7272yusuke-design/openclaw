from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, Optional
from enum import Enum

class ActionType(str, Enum):
    SWAP = "swap"
    LIQUIDITY_PROVISION = "liquidity_provision"
    RISK_HEDGING = "risk_hedging"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AcpPayload(BaseModel):
    action_type: ActionType = Field(..., description="Type of on-chain operation")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters"
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Risk tolerance level for the operation"
    )

class AcpSchema(BaseModel):
    status: Literal["pending", "executing", "completed", "failed"] = Field(
        default="pending",
        description="Current execution status"
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Human-readable operation summary"
    )
    acp_payload: AcpPayload = Field(
        ...,
        description="Core payload for ACP operations"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "pending",
                "summary": "Swap 1 ETH to USDC with 0.5% slippage tolerance",
                "acp_payload": {
                    "action_type": "swap",
                    "parameters": {
                        "from_token": "ETH",
                        "to_token": "USDC",
                        "amount": 1.0,
                        "slippage": 0.5
                    },
                    "risk_level": "medium"
                }
            }
        }
