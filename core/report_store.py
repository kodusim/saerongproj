"""
보고서 생성 기록 저장소.

스토리지: JSON 파일 (core/reports.json).
한 건 구조:
  {
    id: "rpt_xxxxxx",
    created_at: ISO UTC,
    author_login_id: str,       # 로그인 사용자 (감사용)
    period: "daily" | "weekly" | "monthly",
    base_date: "YYYY-MM-DD",    # 기준일 (일/주/월)
    org: str,                   # 소속 기관
    department: str,            # 담당부서
    writer_name: str,
    writer_title: str,          # 직위
    reviewer_name, reviewer_title,
    approver_name, approver_title,
    summary: {...},             # 생성 시점 데이터 스냅샷
    report_text: str,           # GPT 생성 본문 (또는 fallback)
    source: str,                # openai:... | fallback
    scoped_device_uuids: [str]  # 본 보고서의 장비 범위
  }
"""
import os
import json
import uuid
import threading
from datetime import datetime

STORE_PATH = os.path.join(os.path.dirname(__file__), 'reports.json')
_LOCK = threading.RLock()


def _load():
    with _LOCK:
        if not os.path.exists(STORE_PATH):
            return []
        try:
            with open(STORE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or []
        except (json.JSONDecodeError, OSError):
            return []


def _save(data):
    with _LOCK:
        tmp = STORE_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STORE_PATH)


def create_report(record):
    data = _load()
    rid = 'rpt_' + uuid.uuid4().hex[:10]
    now = datetime.utcnow().isoformat() + 'Z'
    record['id'] = rid
    record['created_at'] = now
    data.append(record)
    # 최대 500건 유지 (오래된 것 제거)
    if len(data) > 500:
        data = data[-500:]
    _save(data)
    return record


def get_report(report_id):
    for r in _load():
        if r.get('id') == report_id:
            return r
    return None


def list_reports(author_login_id=None, limit=200):
    """기록 목록.
    author_login_id: None=전체 (admin용), 값=해당 사용자만
    """
    data = _load()
    if author_login_id:
        data = [r for r in data if r.get('author_login_id') == author_login_id]
    data.sort(key=lambda r: r.get('created_at') or '', reverse=True)
    return data[:limit]


def delete_report(report_id):
    data = _load()
    new_data = [r for r in data if r.get('id') != report_id]
    if len(new_data) == len(data):
        raise ValueError('존재하지 않는 보고서')
    _save(new_data)
    return True


# ── 기간 범위 도우미 ────────────────────────────────
def period_range(period, base_date):
    """기준일과 기간 종류로 (start_date, end_date) 문자열 쌍 반환."""
    from datetime import date, timedelta
    if isinstance(base_date, str):
        try:
            d = datetime.strptime(base_date, '%Y-%m-%d').date()
        except Exception:
            d = date.today()
    else:
        d = base_date
    if period == 'weekly':
        start = d - timedelta(days=6)
        end = d
    elif period == 'monthly':
        start = d - timedelta(days=29)
        end = d
    else:
        start = d
        end = d
    return start.isoformat(), end.isoformat()
