from pydantic import BaseModel, Field


class ReportOutput(BaseModel):
    bull_points: list[str] = Field(default_factory=list)
    bear_points: list[str] = Field(default_factory=list)
    overall_summary: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.5)
