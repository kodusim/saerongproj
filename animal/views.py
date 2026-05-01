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

from .models import GuildMember


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
