"""기존 Django 가 만든 테이블에 그대로 매핑한다 — 스키마 변경 없음.

테이블/컬럼 이름은 Django 명명 규칙(`<app>_<model>`)을 유지한다.
`sender_ip` / `author_ip` 는 PostgreSQL `inet` 이라 asyncpg 가 ipaddress 객체로
돌려주므로, 직렬화할 때 str() 로 변환한다 (`app/schemas.py` 참고).
"""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
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
    """자료실과 공지사항이 같은 테이블을 쓴다 — `board` 로만 갈린다.

    글의 생김새(제목/작성자/본문/조회수)가 똑같아서 테이블과 API 를 나눌 이유가
    없었다. 프런트도 `board.js` 하나를 인스턴스 두 개로 돌린다.
    """

    __tablename__ = 'work_workpost'

    BOARDS = ('archive', 'notice')

    CATEGORY_LABELS = {
        'novel': '소설',
        'essay': '수필',
        'etc': '기타',
        # 공지사항용
        'notice': '공지',
        'event': '행사',
    }

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    board: Mapped[str] = mapped_column(String(16), default='archive', nullable=False)
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


class WorkFarm(Base):
    """농장 게임 저장 — 로그인이 없어서 IP 로 사람을 가른다.

    채팅·게시판이 이미 IP 로 '내 글' 을 가리고 있어서 같은 기준을 쓴다.
    (같은 공유기를 쓰면 농장을 공유하게 되지만, 몇 명 쓰는 사내 도구라 충분하다.)
    """

    __tablename__ = 'work_workfarm'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_ip: Mapped[Any] = mapped_column(INET, unique=True, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(32), default='익명 농부', nullable=False)
    money: Mapped[int] = mapped_column(BigInteger, default=50, nullable=False)
    # [{'crop': 'radish', 'planted_at': ISO} | null, ...] — 심은 시각만 두고
    # 다 자랐는지는 그때그때 계산한다 (배치 작업이 필요 없다)
    plots: Mapped[Any] = mapped_column(JSONB, default=list, nullable=False)
    buildings: Mapped[Any] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class WorkGameSave(Base):
    """게임 저장 슬롯 — 게임마다 테이블을 만들지 않으려고 하나로 쓴다.

    `data` 안의 내용은 게임이 알아서 정한다. 서버는 크기만 본다.
    시뮬레이션(이동·타일·하루 넘김)을 서버에서 돌리는 건 현실적이지 않아서
    이 저장은 **클라이언트를 믿는다**. 혼자 하는 게임이라 조작해도 자기 손해고,
    순위가 걸린 `work_workfarm` 쪽은 서버가 계산하므로 영향이 없다.
    """

    __tablename__ = 'work_gamesave'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_ip: Mapped[Any] = mapped_column(INET, nullable=False)
    game: Mapped[str] = mapped_column(String(32), nullable=False)
    data: Mapped[Any] = mapped_column(JSONB, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class BlSeries(Base):
    """작품 — `/bltest` 소설 플랫폼의 연재 단위.

    1차는 계정이 없어서 `author_key`(브라우저 localStorage 에 둔 랜덤 토큰)로
    작가를 가른다. IP 로 가르면 공유기 재접속·모바일 전환만으로 작가가 작품
    수정 권한을 잃기 때문이다 (`work_*` 테이블들과 이 부분이 다르다).

    `author_user_id` 는 2차(계정)에서 채운다 — 그때 author_key 를 승계한다.
    """

    __tablename__ = 'bl_series'

    RATINGS = ('all', 'teen', 'adult')
    STATUSES = ('ongoing', 'done', 'hiatus')

    RATING_LABELS = {'all': '전체이용가', 'teen': '15세', 'adult': '성인'}
    STATUS_LABELS = {'ongoing': '연재중', 'done': '완결', 'hiatus': '휴재'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    author_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    author_name: Mapped[str] = mapped_column(String(32), default='익명', nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default='', nullable=False)
    tags: Mapped[Any] = mapped_column(JSONB, default=list, nullable=False)
    # 1차는 계정이 없어 연령 확인을 할 수 없다 → 'adult' 는 등록 자체를 막는다.
    rating: Mapped[str] = mapped_column(String(8), default='all', nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='ongoing', nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    # 2차(계정)용 자리 — 지금은 항상 NULL
    author_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    @property
    def rating_label(self) -> str:
        return self.RATING_LABELS.get(self.rating, self.rating)

    @property
    def status_label(self) -> str:
        return self.STATUS_LABELS.get(self.status, self.status)


class BlEpisode(Base):
    """회차 — 작품에 딸린 한 편.

    `published_at` 이 NULL 이면 임시저장(작가만 볼 수 있다).
    `is_free` / `price` 는 3차(유료화)용 자리다 — 지금은 항상 무료.
    """

    __tablename__ = 'bl_episode'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    series_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey('bl_series.id', ondelete='CASCADE'), index=True,
        nullable=False,
    )
    no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, default='', nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    # 3차(유료화)용 자리
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BlReport(Base):
    """신고 — 작품/회차를 대상으로 한다.

    누구나 로그인 없이 신고할 수 있어서 도배를 막을 장치가 IP 밖에 없다.
    운영자가 큐에서 보고 조치한다.
    """

    __tablename__ = 'bl_report'

    TARGETS = ('series', 'episode')

    REASONS = {
        'minor': '미성년자 성적 묘사',
        'nonconsent': '동의 없는 성적 콘텐츠',
        'realperson': '실존 인물 대상',
        'copyright': '저작권 침해',
        'rating': '등급 표기 오류',
        'etc': '기타',
    }

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), default='etc', nullable=False)
    detail: Mapped[str] = mapped_column(Text, default='', nullable=False)
    reporter_ip: Mapped[Optional[Any]] = mapped_column(INET, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default='open', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    @property
    def reason_label(self) -> str:
        return self.REASONS.get(self.reason, self.reason)


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
