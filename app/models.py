"""TDM 예측 감사 로그. 기존 테이블 이름과 스키마를 유지한다."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PredictionLog(Base):
    """TDM 예측 감사 로그 — 모든 요청의 입력/결과 JSON 을 남긴다."""

    __tablename__ = 'tdm_predictionlog'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    login_id: Mapped[str] = mapped_column(String(64), default='', nullable=False)
    input_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    ml_model: Mapped[str] = mapped_column(String(32), default='', nullable=False)
    dl_model: Mapped[str] = mapped_column(String(32), default='', nullable=False)
