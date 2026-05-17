"""모스콤 운영 정책 기준 시간 헬퍼.

운영 정책:
- 모기 측정 = 18:00 ~ 다음날 05:00 (KST)
- "하루" = 새벽 05:00 ~ 다음날 새벽 05:00 (KST)
- 즉, 새벽 5시가 일 단위 경계점이며 그때 데이터가 확정됨

함수 예:
  business_today()  → 영업일 기준 오늘 (date)
    KST 5/17 03:00 → date(2026,5,16)
    KST 5/17 06:00 → date(2026,5,17)
"""
from datetime import datetime, date, timedelta, timezone

KST = timezone(timedelta(hours=9))
DAY_CUTOFF_HOUR = 5  # 새벽 5시 기준


def kst_now():
    return datetime.now(KST)


def business_today(now=None):
    """새벽 5시 기준 '오늘' 영업일.
    - 자정 ~ 04:59 사이는 전날로 처리
    - 05:00 ~ 23:59 사이는 그날로 처리
    """
    if now is None:
        now = kst_now()
    elif now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    if now.hour < DAY_CUTOFF_HOUR:
        return (now - timedelta(days=1)).date()
    return now.date()


def business_yesterday(now=None):
    """영업일 어제 (기본 영업일 - 1)."""
    return business_today(now) - timedelta(days=1)


def is_measuring_now(now=None):
    """현재 측정 시간대(18:00~05:00 KST)인지."""
    if now is None:
        now = kst_now()
    elif now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    h = now.hour
    return h >= 18 or h < DAY_CUTOFF_HOUR


def business_day_range_utc(d):
    """date d 의 영업일 시작/끝 UTC datetime.
    Returns (start_utc, end_utc) — Collection 쿼리에 그대로 사용 가능.
    """
    # d 의 영업일 = d일 05:00 KST ~ d+1일 05:00 KST
    start_kst = datetime.combine(d, datetime.min.time(), tzinfo=KST).replace(hour=DAY_CUTOFF_HOUR)
    end_kst = start_kst + timedelta(days=1)
    return start_kst.astimezone(timezone.utc), end_kst.astimezone(timezone.utc)
