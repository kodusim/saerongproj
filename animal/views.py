"""
Animal app — 길드 운영 도구.

공개 페이지 (/animal/) — 누구나 접근 가능, 읽기 전용
관리자 로그인 (/animal/login/) — admin_an / admin
관리자 API — 세션 인증 후 길드원 CRUD
"""
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Max

import re
from datetime import datetime, date
from django.utils import timezone

from .models import (
    GuildMember, CollectibleItem, MemberCollectible, EquipSlot, MemberEquip,
    Boss, BossWeek, BossClear, BossClearParticipant,
)


CATEGORY_LABELS = dict(CollectibleItem.CATEGORY_CHOICES)
CATEGORY_KEYS = [k for k, _ in CollectibleItem.CATEGORY_CHOICES]
SECTION_LABELS = dict(EquipSlot.SECTION_CHOICES)
EQUIP_STATUS = dict(MemberEquip.STATUS_CHOICES)


def _normalize_boss_name(raw):
    """입력된 보스명에서 끝의 숫자/공백 제거. '베나투스1' → '베나투스', '4.30 베나투스2' 같은 케이스도 처리."""
    if not raw:
        return ''
    s = raw.strip()
    # 끝에 붙은 숫자(1, 2, 트라이 등) 제거
    s = re.sub(r'\d+\s*$', '', s).strip()
    # 트라이 같은 접미사 제거
    s = re.sub(r'트라이\s*$', '', s).strip()
    return s


ADMIN_ID = 'admin_an'
ADMIN_PW = 'admin'


def _is_admin(request):
    return bool(request.session.get('animal_admin'))


# ─ 페이지 ──────────────────────────────────────────────

def animal_view(request):
    """누구나 접근 가능한 길드 운영 페이지."""
    return render(request, 'animal/animal_page.html', {
        'is_admin': _is_admin(request),
    })


def animal_login(request):
    """관리자 로그인 페이지."""
    if _is_admin(request):
        return redirect('/animal/')
    error = ''
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        if username == ADMIN_ID and password == ADMIN_PW:
            request.session['animal_admin'] = True
            return redirect('/animal/')
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render(request, 'animal/animal_login.html', {'error': error})


def animal_logout(request):
    if 'animal_admin' in request.session:
        del request.session['animal_admin']
    return redirect('/animal/')


# ─ API ────────────────────────────────────────────────

@require_GET
def member_list_api(request):
    """길드원 전체 목록 (공개)."""
    qs = GuildMember.objects.filter(active=True).order_by('order', 'id')
    items = [
        {
            'id': m.id,
            'order': i + 1,           # 화면 연번은 1..N 자동 재계산
            'nickname': m.nickname,
            'power': m.power,
            'weapon': m.weapon,
        }
        for i, m in enumerate(qs)
    ]
    return JsonResponse({'count': len(items), 'items': items, 'is_admin': _is_admin(request)})


@csrf_exempt
@require_POST
def member_create_api(request):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    nickname = (body.get('nickname') or '').strip()
    if not nickname:
        return JsonResponse({'error': '닉네임은 필수입니다'}, status=400)
    if GuildMember.objects.filter(nickname=nickname).exists():
        return JsonResponse({'error': '이미 존재하는 닉네임입니다'}, status=400)
    try:
        power = int(body.get('power') or 0)
    except (TypeError, ValueError):
        power = 0
    weapon = (body.get('weapon') or '').strip()[:100]
    next_order = (GuildMember.objects.aggregate(Max('order'))['order__max'] or 0) + 1
    m = GuildMember.objects.create(
        nickname=nickname, power=power, weapon=weapon, order=next_order, active=True,
    )
    return JsonResponse({'ok': True, 'id': m.id})


@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def member_detail_api(request, member_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        m = GuildMember.objects.get(id=member_id)
    except GuildMember.DoesNotExist:
        return JsonResponse({'error': '존재하지 않는 길드원'}, status=404)

    if request.method in ('PUT', 'PATCH'):
        try:
            body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
        except json.JSONDecodeError:
            body = {}
        if 'nickname' in body:
            new_nick = (body.get('nickname') or '').strip()
            if not new_nick:
                return JsonResponse({'error': '닉네임은 필수입니다'}, status=400)
            if GuildMember.objects.exclude(id=m.id).filter(nickname=new_nick).exists():
                return JsonResponse({'error': '이미 존재하는 닉네임입니다'}, status=400)
            m.nickname = new_nick
        if 'power' in body:
            try:
                m.power = int(body.get('power') or 0)
            except (TypeError, ValueError):
                pass
        if 'weapon' in body:
            m.weapon = (body.get('weapon') or '').strip()[:100]
        m.save()
        return JsonResponse({'ok': True})

    # DELETE
    with transaction.atomic():
        m.delete()
        # 연번 재정렬 — 남은 길드원의 order를 1부터 다시 부여
        for i, x in enumerate(GuildMember.objects.filter(active=True).order_by('order', 'id'), start=1):
            if x.order != i:
                x.order = i
                x.save(update_fields=['order'])
    return JsonResponse({'ok': True})


# ─ 컬렉용 아이템 API ────────────────────────────────

@require_GET
def collectibles_api(request):
    """카테고리별 컬렉용 매트릭스. 길드원은 전투력 내림차순."""
    category = (request.GET.get('category') or 'accessory').strip()
    if category not in CATEGORY_LABELS:
        return JsonResponse({'error': '잘못된 카테고리'}, status=400)
    items = list(
        CollectibleItem.objects.filter(category=category).order_by('order', 'id')
    )
    members = list(
        GuildMember.objects.filter(active=True).order_by('-power', 'order', 'id')
    )
    item_ids = [it.id for it in items]
    member_ids = [m.id for m in members]
    owned_set = set(
        MemberCollectible.objects
        .filter(member_id__in=member_ids, item_id__in=item_ids, owned=True)
        .values_list('member_id', 'item_id')
    )
    return JsonResponse({
        'category': category,
        'category_label': CATEGORY_LABELS[category],
        'categories': [{'key': k, 'label': v} for k, v in CollectibleItem.CATEGORY_CHOICES],
        'items': [{'id': it.id, 'name': it.name, 'order': it.order} for it in items],
        'members': [
            {'id': m.id, 'nickname': m.nickname, 'power': m.power, 'weapon': m.weapon}
            for m in members
        ],
        'owned': [[mid, iid] for (mid, iid) in owned_set],
        'is_admin': _is_admin(request),
    })


@csrf_exempt
@require_POST
def collectible_toggle_api(request):
    """{member_id, item_id, owned: bool} — 관리자만."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    try:
        member_id = int(body.get('member_id'))
        item_id = int(body.get('item_id'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'member_id, item_id 필요'}, status=400)
    owned = bool(body.get('owned'))
    if not GuildMember.objects.filter(id=member_id, active=True).exists():
        return JsonResponse({'error': '존재하지 않는 길드원'}, status=404)
    if not CollectibleItem.objects.filter(id=item_id).exists():
        return JsonResponse({'error': '존재하지 않는 아이템'}, status=404)
    obj, _created = MemberCollectible.objects.update_or_create(
        member_id=member_id, item_id=item_id, defaults={'owned': owned}
    )
    return JsonResponse({'ok': True, 'owned': obj.owned})


# ─ 장비 내판 API ────────────────────────────────────

@require_GET
def equips_api(request):
    """섹션별 장비 내판 매트릭스. 길드원은 전투력 내림차순."""
    section = (request.GET.get('section') or 'equip').strip()
    if section not in SECTION_LABELS:
        return JsonResponse({'error': '잘못된 섹션'}, status=400)
    slots = list(EquipSlot.objects.filter(section=section).order_by('order', 'id'))
    members = list(GuildMember.objects.filter(active=True).order_by('-power', 'order', 'id'))
    slot_ids = [s.id for s in slots]
    member_ids = [m.id for m in members]
    # status map: {(member_id, slot_id): status}
    status_map = {}
    for me in MemberEquip.objects.filter(
        member_id__in=member_ids, slot_id__in=slot_ids
    ).exclude(status='none'):
        status_map[(me.member_id, me.slot_id)] = me.status
    return JsonResponse({
        'section': section,
        'section_label': SECTION_LABELS[section],
        'sections': [{'key': k, 'label': v} for k, v in EquipSlot.SECTION_CHOICES],
        'statuses': [{'key': k, 'label': v} for k, v in MemberEquip.STATUS_CHOICES],
        'slots': [{'id': s.id, 'name': s.name, 'order': s.order} for s in slots],
        'members': [
            {'id': m.id, 'nickname': m.nickname, 'power': m.power, 'weapon': m.weapon}
            for m in members
        ],
        'entries': [[mid, sid, st] for (mid, sid), st in status_map.items()],
        'is_admin': _is_admin(request),
    })


@csrf_exempt
@require_POST
def equip_set_api(request):
    """{member_id, slot_id, status} — 관리자만."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    try:
        member_id = int(body.get('member_id'))
        slot_id = int(body.get('slot_id'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'member_id, slot_id 필요'}, status=400)
    status = (body.get('status') or 'none').strip()
    if status not in EQUIP_STATUS:
        return JsonResponse({'error': '잘못된 status'}, status=400)
    if not GuildMember.objects.filter(id=member_id, active=True).exists():
        return JsonResponse({'error': '존재하지 않는 길드원'}, status=404)
    if not EquipSlot.objects.filter(id=slot_id).exists():
        return JsonResponse({'error': '존재하지 않는 슬롯'}, status=404)
    if status == 'none':
        # 미소유는 행 없음으로 표현 (저장 공간 절약)
        MemberEquip.objects.filter(member_id=member_id, slot_id=slot_id).delete()
    else:
        MemberEquip.objects.update_or_create(
            member_id=member_id, slot_id=slot_id, defaults={'status': status}
        )
    return JsonResponse({'ok': True, 'status': status})


# ─ 보스 마스터 ────────────────────────────────────

@require_GET
def boss_list_api(request):
    bosses = list(Boss.objects.all())
    return JsonResponse({
        'items': [{'id': b.id, 'name': b.name, 'score': b.score, 'order': b.order} for b in bosses],
        'is_admin': _is_admin(request),
    })


@csrf_exempt
@require_POST
def boss_create_api(request):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    name = (body.get('name') or '').strip()
    if not name:
        return JsonResponse({'error': '보스명은 필수입니다'}, status=400)
    if Boss.objects.filter(name=name).exists():
        return JsonResponse({'error': '이미 등록된 보스입니다'}, status=400)
    try:
        score = int(body.get('score') or 1)
    except (TypeError, ValueError):
        score = 1
    next_order = (Boss.objects.aggregate(Max('order'))['order__max'] or 0) + 1
    b = Boss.objects.create(name=name, score=score, order=next_order)
    return JsonResponse({'ok': True, 'id': b.id})


@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def boss_detail_api(request, boss_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        b = Boss.objects.get(id=boss_id)
    except Boss.DoesNotExist:
        return JsonResponse({'error': '존재하지 않는 보스'}, status=404)
    if request.method in ('PUT', 'PATCH'):
        try:
            body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
        except json.JSONDecodeError:
            body = {}
        if 'name' in body:
            new_name = (body.get('name') or '').strip()
            if not new_name:
                return JsonResponse({'error': '보스명 필수'}, status=400)
            if Boss.objects.exclude(id=b.id).filter(name=new_name).exists():
                return JsonResponse({'error': '이미 존재하는 보스명'}, status=400)
            b.name = new_name
        if 'score' in body:
            try:
                b.score = int(body.get('score') or 0)
            except (TypeError, ValueError):
                pass
        b.save()
        # 이름이 바뀌면 정규화 매칭이 달라질 수 있으니, 모든 BossClear 재매칭
        _rematch_clears()
        return JsonResponse({'ok': True})
    # DELETE
    b.delete()
    _rematch_clears()
    return JsonResponse({'ok': True})


def _rematch_clears():
    """BossClear의 boss FK를 모든 보스 마스터에 대해 재매칭."""
    name_to_boss = {bs.name: bs for bs in Boss.objects.all()}
    for cl in BossClear.objects.all():
        norm = _normalize_boss_name(cl.boss_name_raw)
        new_boss = name_to_boss.get(norm)
        if cl.boss_id != (new_boss.id if new_boss else None):
            cl.boss = new_boss
            cl.save(update_fields=['boss'])


# ─ 주차 관리 ─────────────────────────────────────

@require_GET
def week_list_api(request):
    weeks = list(BossWeek.objects.order_by('-start_date', '-id'))
    cur = next((w for w in weeks if w.is_current), None)
    return JsonResponse({
        'weeks': [
            {
                'id': w.id, 'name': w.name,
                'start_date': w.start_date.isoformat(),
                'is_current': w.is_current,
                'closed_at': w.closed_at.isoformat() if w.closed_at else None,
            } for w in weeks
        ],
        'current_id': cur.id if cur else None,
        'is_admin': _is_admin(request),
    })


@csrf_exempt
@require_POST
def week_create_api(request):
    """첫 주차 또는 분배 종료 후 새 주차 생성. 기존 current 가 있으면 닫고 새 것을 current 로."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    name = (body.get('name') or '').strip()
    start_date_str = (body.get('start_date') or '').strip()
    if not name:
        return JsonResponse({'error': '주차명 필수'}, status=400)
    if BossWeek.objects.filter(name=name).exists():
        return JsonResponse({'error': '이미 존재하는 주차명'}, status=400)
    try:
        sd = date.fromisoformat(start_date_str) if start_date_str else timezone.localdate()
    except ValueError:
        return JsonResponse({'error': '시작일 형식 오류 (YYYY-MM-DD)'}, status=400)
    with transaction.atomic():
        # 기존 현재 주차가 있으면 닫음
        BossWeek.objects.filter(is_current=True).update(is_current=False)
        for w in BossWeek.objects.filter(closed_at__isnull=True):
            w.closed_at = timezone.now()
            w.save(update_fields=['closed_at'])
        new_w = BossWeek.objects.create(name=name, start_date=sd, is_current=True)
    return JsonResponse({'ok': True, 'id': new_w.id})


@csrf_exempt
@require_POST
def week_close_api(request):
    """현재 주차 분배 종료. (다음 주차는 자동으로 만들지 않음 — 새 주차는 별도 생성)"""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    cur = BossWeek.objects.filter(is_current=True).first()
    if not cur:
        return JsonResponse({'error': '활성 주차가 없습니다'}, status=400)
    cur.is_current = False
    cur.closed_at = timezone.now()
    cur.save(update_fields=['is_current', 'closed_at'])
    return JsonResponse({'ok': True})


# ─ 보스 토벌 (BossClear) ────────────────────────

@require_GET
def boss_clears_api(request):
    """주차별 토벌 목록 + 길드원별 합계."""
    week_id = request.GET.get('week_id')
    week = None
    if week_id:
        week = BossWeek.objects.filter(id=week_id).first()
    else:
        week = BossWeek.objects.filter(is_current=True).first()
        if not week:
            week = BossWeek.objects.order_by('-start_date', '-id').first()
    if not week:
        return JsonResponse({
            'week': None, 'clears': [], 'totals': [],
            'members': [], 'bosses': [],
            'is_admin': _is_admin(request),
        })

    # 토벌
    clears = list(
        BossClear.objects
        .filter(week=week)
        .select_related('boss')
        .prefetch_related('participants__member')
        .order_by('-date', '-time')
    )
    members_qs = GuildMember.objects.filter(active=True).order_by('order', 'id')
    member_order = {m.id: i for i, m in enumerate(members_qs)}
    members = list(members_qs)

    clears_payload = []
    totals = {m.id: 0 for m in members}
    boss_counts = {m.id: 0 for m in members}
    war_counts = {m.id: 0 for m in members}
    week_total_score = 0
    for c in clears:
        score = c.effective_score
        is_war = '쟁' in (c.note or '')
        # 참여자 — 길드원 order 순으로 정렬
        parts = sorted(
            (p.member for p in c.participants.all()),
            key=lambda m: member_order.get(m.id, 9999),
        )
        for m in parts:
            if m.id in totals:
                totals[m.id] += score
                boss_counts[m.id] += 1
                if is_war:
                    war_counts[m.id] += 1
        # 주차 전체 점수: 토벌마다 (점수 × 참여자수)
        week_total_score += score * len(parts)
        clears_payload.append({
            'id': c.id,
            'date': c.date.isoformat(),
            'time': c.time.strftime('%H:%M:%S'),
            'boss_name_raw': c.boss_name_raw,
            'boss_name': c.boss.name if c.boss else None,
            'matched': bool(c.boss),
            'score': score,
            'score_override': c.score_override,
            'note': c.note,
            'participant_ids': [m.id for m in parts],
            'participant_names': [m.nickname for m in parts],
        })

    return JsonResponse({
        'week': {
            'id': week.id, 'name': week.name,
            'start_date': week.start_date.isoformat(),
            'is_current': week.is_current,
            'closed_at': week.closed_at.isoformat() if week.closed_at else None,
        },
        'clears': clears_payload,
        'week_total_score': week_total_score,
        'totals': [
            {
                'member_id': m.id, 'nickname': m.nickname,
                'order': member_order[m.id] + 1,
                'score': totals[m.id],
                'boss_count': boss_counts[m.id],
                'war_count': war_counts[m.id],
            }
            for m in members
        ],
        'is_admin': _is_admin(request),
    })


@csrf_exempt
@require_POST
def boss_clear_ingest_api(request):
    """텍스트 통째 입력 → 파싱해서 BossClear + Participants 일괄 생성."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    text = (body.get('text') or '')
    week_id = body.get('week_id')

    week = None
    if week_id:
        week = BossWeek.objects.filter(id=week_id).first()
    if not week:
        week = BossWeek.objects.filter(is_current=True).first()
    if not week:
        return JsonResponse({'error': '활성 주차가 없습니다. 먼저 주차를 생성하세요.'}, status=400)
    if not week.is_current:
        return JsonResponse({'error': '현재 주차에만 입력할 수 있습니다.'}, status=400)

    members = {m.nickname: m for m in GuildMember.objects.filter(active=True)}
    name_to_boss = {b.name: b for b in Boss.objects.all()}

    parsed = []  # list of dicts to insert
    duplicates = []  # (date, time, boss) already in DB
    unknown_members = set()  # nicknames not in roster
    unmatched_bosses = set()  # boss names without master entry
    errors = []  # parse errors per row

    lines = [ln for ln in text.replace('\r', '\n').split('\n') if ln.strip()]
    for raw_line in lines:
        # 헤더 라인 무시
        first = raw_line.split('\t')[0].strip()
        if first == '날짜':
            continue
        cols = raw_line.split('\t')
        # 날짜 시간 보스 (획득) (컷자) 참여자 — 5컬럼 또는 6컬럼
        if len(cols) < 4:
            errors.append({'line': raw_line, 'reason': '컬럼 부족 (탭 구분)'})
            continue
        date_str = cols[0].strip()
        time_str = cols[1].strip()
        boss_raw = cols[2].strip()
        # 참여자는 마지막 컬럼
        participants_str = cols[-1].strip()
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            errors.append({'line': raw_line, 'reason': f'날짜 형식 오류: {date_str}'})
            continue
        try:
            t = datetime.strptime(time_str, '%H:%M:%S').time()
        except ValueError:
            try:
                t = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                errors.append({'line': raw_line, 'reason': f'시간 형식 오류: {time_str}'})
                continue
        if not boss_raw:
            errors.append({'line': raw_line, 'reason': '보스명 비어있음'})
            continue
        # 참여자 파싱 (쉼표 구분)
        nicks = [n.strip() for n in participants_str.split(',') if n.strip()]
        # 매칭
        norm = _normalize_boss_name(boss_raw)
        boss_obj = name_to_boss.get(norm)
        if not boss_obj:
            unmatched_bosses.add(norm or boss_raw)
        match_ids = []
        for nick in nicks:
            m = members.get(nick)
            if m:
                match_ids.append(m.id)
            else:
                unknown_members.add(nick)
        # 중복 체크 (DB)
        if BossClear.objects.filter(week=week, date=d, time=t, boss_name_raw=boss_raw).exists():
            duplicates.append(f'{date_str} {time_str} {boss_raw}')
            continue
        parsed.append({
            'date': d, 'time': t, 'boss_name_raw': boss_raw, 'boss': boss_obj,
            'participant_ids': match_ids,
        })

    if duplicates:
        return JsonResponse({
            'error': '중복 데이터 발견. 엑셀에서 행을 삭제 후 입력하세요.',
            'duplicates': duplicates,
        }, status=400)

    # 같은 입력 안에서 중복 체크
    seen = set()
    for p in parsed:
        key = (p['date'], p['time'], p['boss_name_raw'])
        if key in seen:
            return JsonResponse({
                'error': '중복 데이터 발견. 엑셀에서 행을 삭제 후 입력하세요.',
                'duplicates': [f'{p["date"]} {p["time"]} {p["boss_name_raw"]}'],
            }, status=400)
        seen.add(key)

    if errors:
        return JsonResponse({
            'error': f'{len(errors)}개 행 파싱 실패',
            'errors': errors[:20],
        }, status=400)

    # 저장
    with transaction.atomic():
        for p in parsed:
            cl = BossClear.objects.create(
                week=week, date=p['date'], time=p['time'],
                boss_name_raw=p['boss_name_raw'], boss=p['boss'],
            )
            for mid in p['participant_ids']:
                BossClearParticipant.objects.create(clear=cl, member_id=mid)

    return JsonResponse({
        'ok': True,
        'created': len(parsed),
        'unknown_members': sorted(unknown_members),
        'unmatched_bosses': sorted(unmatched_bosses),
    })


@csrf_exempt
@require_POST
def boss_clear_participant_add_api(request, clear_id):
    """{member_id} 또는 {nickname} — 토벌에 참여자 추가."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        c = BossClear.objects.get(id=clear_id)
    except BossClear.DoesNotExist:
        return JsonResponse({'error': '존재하지 않는 토벌'}, status=404)
    if not c.week.is_current:
        return JsonResponse({'error': '과거 주차는 수정할 수 없습니다'}, status=400)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    m = None
    if body.get('member_id'):
        try:
            m = GuildMember.objects.get(id=int(body['member_id']), active=True)
        except (GuildMember.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'error': '존재하지 않는 길드원'}, status=404)
    else:
        nick = (body.get('nickname') or '').strip()
        if not nick:
            return JsonResponse({'error': 'member_id 또는 nickname 필요'}, status=400)
        m = GuildMember.objects.filter(nickname=nick, active=True).first()
        if not m:
            return JsonResponse({'error': f'길드원 명단에 없음: {nick}'}, status=404)
    obj, created = BossClearParticipant.objects.get_or_create(clear=c, member=m)
    return JsonResponse({'ok': True, 'created': created, 'member': {'id': m.id, 'nickname': m.nickname}})


@csrf_exempt
@require_http_methods(['DELETE'])
def boss_clear_participant_remove_api(request, clear_id, member_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        c = BossClear.objects.get(id=clear_id)
    except BossClear.DoesNotExist:
        return JsonResponse({'error': '존재하지 않는 토벌'}, status=404)
    if not c.week.is_current:
        return JsonResponse({'error': '과거 주차는 수정할 수 없습니다'}, status=400)
    BossClearParticipant.objects.filter(clear=c, member_id=member_id).delete()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def boss_clear_detail_api(request, clear_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        c = BossClear.objects.get(id=clear_id)
    except BossClear.DoesNotExist:
        return JsonResponse({'error': '존재하지 않는 토벌'}, status=404)
    if not c.week.is_current:
        return JsonResponse({'error': '과거 주차는 수정할 수 없습니다'}, status=400)
    if request.method in ('PUT', 'PATCH'):
        try:
            body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
        except json.JSONDecodeError:
            body = {}
        if 'score_override' in body:
            v = body.get('score_override')
            if v in (None, '', 'null'):
                c.score_override = None
            else:
                try:
                    c.score_override = int(v)
                except (TypeError, ValueError):
                    return JsonResponse({'error': '점수 형식 오류'}, status=400)
        if 'note' in body:
            c.note = (body.get('note') or '').strip()[:200]
        c.save()
        return JsonResponse({'ok': True})
    # DELETE
    c.delete()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def member_reorder_api(request):
    """드래그앤드롭 등으로 순서 변경.
    body: {ids: [member_id, ...]}  새 순서대로 ID 배열
    """
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    ids = body.get('ids') or []
    if not isinstance(ids, list):
        return JsonResponse({'error': 'ids 배열 필요'}, status=400)
    with transaction.atomic():
        for i, mid in enumerate(ids, start=1):
            GuildMember.objects.filter(id=mid).update(order=i)
    return JsonResponse({'ok': True})
