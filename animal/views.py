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

from .models import GuildMember, CollectibleItem, MemberCollectible, EquipSlot, MemberEquip


CATEGORY_LABELS = dict(CollectibleItem.CATEGORY_CHOICES)
CATEGORY_KEYS = [k for k, _ in CollectibleItem.CATEGORY_CHOICES]
SECTION_LABELS = dict(EquipSlot.SECTION_CHOICES)
EQUIP_STATUS = dict(MemberEquip.STATUS_CHOICES)


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
