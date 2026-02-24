from pydantic import BaseModel, Field
from typing import Optional

class CrewResult(BaseModel):
    status: str = Field(description="success または failed")
    summary: str = Field(description="実行したタスクの簡潔な要約（200文字以内）")
    virtuals_payload: Optional[dict] = Field(description="Virtuals Protocol(ACP)へ送信するためのJSONデータ")
    next_action_suggestion: str = Field(description="OpenClawが次に取るべき行動の提案")
