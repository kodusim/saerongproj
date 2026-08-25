"""기존 Django 가 만든 테이블에 그대로 매핑한다 — 스키마 변경 없음.

테이블/컬럼 이름은 Django 명명 규칙(`<app>_<model>`)을 유지한다.
`sender_ip` / `author_ip` 는 PostgreSQL `inet` 이라 asyncpg 가 ipaddress 객체로
돌려주므로, 직렬화할 때 str() 로 변환한다 (`app/schemas.py` 참고).
"""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
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


class WorkChatMessage(Base):
    __tablename__ = 'work_workchatmessage'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sender_name: Mapped[str] = mapped_column(String(32), default='익명', nullable=False)
    sender_ip: Mapped[Optional[Any]] = mapped_column(INET, nullable=True)
    body: Mapped[str] = mapped_column(Text, default='', nullable=False)
    # Django ImageField 가 남긴 MEDIA_ROOT 기준 상대 경로 (예: work/chat/2026/08/a.png)
    image: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class WorkPost(Base):
    __tablename__ = 'work_workpost'

    CATEGORY_LABELS = {
        'novel': '소설',
        'essay': '수필',
        'etc': '기타',
    }

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category: Mapped[str] = mapped_column(String(16), default='novel', nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author_name: Mapped[str] = mapped_column(String(32), default='익명', nullable=False)
    author_ip: Mapped[Optional[Any]] = mapped_column(INET, nullable=True)
    body: Mapped[str] = mapped_column(Text, default='', nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    @property
    def category_label(self) -> str:
        return self.CATEGORY_LABELS.get(self.category, self.category)


class WorkSchedule(Base):
    """만남 일정 — 그룹웨어의 '설비예약' 탭으로 보인다.

    FastAPI 로 넘어온 뒤 처음 새로 만든 테이블이라 Django 흔적이 없다.
    다만 이름 규칙(`work_<model>`)은 나머지와 맞춘다.
    """

    __tablename__ = 'work_workschedule'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 날짜만 잡고 시간은 미정일 수 있어서 분리해 둔다 (시간은 빈 문자열 허용)
    meet_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meet_time: Mapped[str] = mapped_column(String(16), default='', nullable=False)
    place: Mapped[str] = mapped_column(String(120), default='', nullable=False)
    attendees: Mapped[str] = mapped_column(String(200), default='', nullable=False)
    memo: Mapped[str] = mapped_column(Text, default='', nullable=False)
    author_name: Mapped[str] = mapped_column(String(32), default='익명', nullable=False)
    author_ip: Mapped[Optional[Any]] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
