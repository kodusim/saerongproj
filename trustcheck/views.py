"""TrustCheck 뷰 — 랜딩 + 러프 백엔드 MVP.

인증은 세션 기반 (플랫폼 전용 TCUser). Django auth 와 분리.
API 는 JSON, 페이지는 템플릿 렌더.
"""
import json
import logging
from functools import wraps

from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import (
    TCUser, ConsultPost, ExpertMessage, ChatRoom, ChatMessage,
    Product, Case, CaseFile, Report,
)

logger = logging.getLogger(__name__)

SESSION_UID = 'tc_uid'


# ---------------------------------------------------------------------------
# 인증 헬퍼
# ---------------------------------------------------------------------------
def current_user(request):
    uid = request.session.get(SESSION_UID)
    if not uid:
        return None
    return TCUser.objects.filter(pk=uid).first()


def login_required_json(view):
    @wraps(view)
    def _wrap(request, *a, **kw):
        user = current_user(request)
        if not user:
            return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
        request.tc_user = user
        return view(request, *a, **kw)
    return _wrap


def role_required_json(*roles):
    def deco(view):
        @wraps(view)
        def _wrap(request, *a, **kw):
            user = current_user(request)
            if not user:
                return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
            if user.role not in roles:
                return JsonResponse({'error': '권한이 없습니다.'}, status=403)
            request.tc_user = user
            return view(request, *a, **kw)
        return _wrap
    return deco


def _body(request):
    try:
        return json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        return {}


def _user_dict(u):
    return {
        'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role,
        'role_display': u.get_role_display(), 'expert_type': u.expert_type,
        'approved': u.approved,
    }


# ---------------------------------------------------------------------------
# 페이지
# ---------------------------------------------------------------------------
@require_GET
def landing(request):
    """랜딩 페이지 (참고 index.html 그대로)."""
    return render(request, 'trustcheck/landing.html', {
        'user': current_user(request),
    })


@require_GET
def app_page(request):
    """로그인 후 대시보드 (러프 SPA-ish 단일 페이지)."""
    user = current_user(request)
    if not user:
        return HttpResponseRedirect(reverse('tc_landing') + '#login')
    return render(request, 'trustcheck/app.html', {'user': user})


# ---------------------------------------------------------------------------
# 인증 API
# ---------------------------------------------------------------------------
@csrf_exempt
@require_POST
def api_signup(request):
    b = _body(request)
    email = (b.get('email') or '').strip().lower()
    pw = (b.get('password') or '').strip()
    name = (b.get('name') or '').strip()
    role = (b.get('role') or TCUser.ROLE_CLIENT).strip()
    expert_type = (b.get('expert_type') or '').strip()

    if not email or not pw or not name:
        return JsonResponse({'error': '이메일·비밀번호·이름은 필수입니다.'}, status=400)
    if role not in (TCUser.ROLE_CLIENT, TCUser.ROLE_EXPERT):
        return JsonResponse({'error': '잘못된 역할입니다.'}, status=400)
    if role == TCUser.ROLE_EXPERT and expert_type not in (TCUser.EXPERT_PM, TCUser.EXPERT_LAWYER):
        return JsonResponse({'error': '전문가 유형(pm/lawyer)을 선택하세요.'}, status=400)
    if TCUser.objects.filter(email=email).exists():
        return JsonResponse({'error': '이미 가입된 이메일입니다.'}, status=409)

    u = TCUser(email=email, name=name, role=role, expert_type=expert_type)
    u.set_password(pw)
    # 전문가는 관리자 승인 전까지 미승인
    u.is_approved = (role != TCUser.ROLE_EXPERT)
    u.save()
    request.session[SESSION_UID] = u.id
    return JsonResponse({'user': _user_dict(u)}, status=201)


@csrf_exempt
@require_POST
def api_login(request):
    b = _body(request)
    email = (b.get('email') or '').strip().lower()
    pw = (b.get('password') or '').strip()
    u = TCUser.objects.filter(email=email).first()
    if not u or not u.check_password(pw):
        return JsonResponse({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}, status=401)
    request.session[SESSION_UID] = u.id
    return JsonResponse({'user': _user_dict(u)})


@csrf_exempt
@require_POST
def api_logout(request):
    request.session.pop(SESSION_UID, None)
    return JsonResponse({'ok': True})


@require_GET
def api_me(request):
    u = current_user(request)
    if not u:
        return JsonResponse({'user': None})
    return JsonResponse({'user': _user_dict(u)})


# ---------------------------------------------------------------------------
# 상담 게시글
# ---------------------------------------------------------------------------
def _post_dict(p, user=None):
    return {
        'id': p.id, 'title': p.title, 'field': p.field,
        'field_display': p.get_field_display(),
        'situation': p.situation, 'budget': p.budget,
        'status': p.status, 'status_display': p.get_status_display(),
        'author': p.author.name, 'author_id': p.author_id,
        'appeal_count': p.appeals.count(),
        'created_at': p.created_at.isoformat(),
        'is_mine': bool(user and p.author_id == user.id),
    }


@csrf_exempt
def api_posts(request):
    """GET: 목록(전문가=분야별 열람 / 발주자=내 글) · POST: 작성(발주자)."""
    user = current_user(request)
    if request.method == 'GET':
        qs = ConsultPost.objects.select_related('author').all()
        field = request.GET.get('field')
        if field:
            qs = qs.filter(field=field)
        mine = request.GET.get('mine')
        if mine and user:
            qs = qs.filter(author=user)
        return JsonResponse({'posts': [_post_dict(p, user) for p in qs[:100]]})

    # POST
    if not user:
        return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
    if user.role != TCUser.ROLE_CLIENT:
        return JsonResponse({'error': '발주자만 게시글을 작성할 수 있습니다.'}, status=403)
    b = _body(request)
    title = (b.get('title') or '').strip()
    situation = (b.get('situation') or '').strip()
    field = (b.get('field') or 'pm').strip()
    if not title or not situation:
        return JsonResponse({'error': '제목·상황은 필수입니다.'}, status=400)
    p = ConsultPost.objects.create(
        author=user, title=title, situation=situation, field=field,
        budget=(b.get('budget') or '').strip(),
    )
    return JsonResponse({'post': _post_dict(p, user)}, status=201)


@require_GET
def api_post_detail(request, post_id):
    p = get_object_or_404(ConsultPost, pk=post_id)
    user = current_user(request)
    data = _post_dict(p, user)
    data['appeals'] = [{
        'id': a.id, 'expert': a.expert.name, 'expert_type': a.expert.expert_type,
        'message': a.message, 'status': a.status, 'expert_id': a.expert_id,
    } for a in p.appeals.select_related('expert').all()]
    return JsonResponse({'post': data})


# ---------------------------------------------------------------------------
# 역매칭 — 어필 / 수락
# ---------------------------------------------------------------------------
@csrf_exempt
@role_required_json(TCUser.ROLE_EXPERT)
@require_POST
def api_appeal(request, post_id):
    user = request.tc_user
    if not user.approved:
        return JsonResponse({'error': '승인 대기중인 전문가입니다.'}, status=403)
    post = get_object_or_404(ConsultPost, pk=post_id)
    b = _body(request)
    msg = (b.get('message') or '').strip()
    if not msg:
        return JsonResponse({'error': '어필 메시지를 입력하세요.'}, status=400)
    if ExpertMessage.objects.filter(post=post, expert=user).exists():
        return JsonResponse({'error': '이미 어필한 게시글입니다.'}, status=409)
    a = ExpertMessage.objects.create(post=post, expert=user, message=msg)
    return JsonResponse({'appeal_id': a.id}, status=201)


@csrf_exempt
@role_required_json(TCUser.ROLE_CLIENT)
@require_POST
def api_appeal_respond(request, appeal_id):
    """발주자가 수락/거절. 수락 시 채팅방 자동 개설."""
    user = request.tc_user
    appeal = get_object_or_404(ExpertMessage.objects.select_related('post', 'expert'), pk=appeal_id)
    if appeal.post.author_id != user.id:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    b = _body(request)
    action = (b.get('action') or '').strip()
    if action == 'reject':
        appeal.status = ExpertMessage.STATUS_REJECTED
        appeal.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'status': appeal.status})
    if action != 'accept':
        return JsonResponse({'error': 'action 은 accept/reject.'}, status=400)

    appeal.status = ExpertMessage.STATUS_ACCEPTED
    appeal.save(update_fields=['status'])
    appeal.post.status = ConsultPost.STATUS_MATCHED
    appeal.post.save(update_fields=['status'])
    room, created = ChatRoom.objects.get_or_create(
        post=appeal.post, client=user, expert=appeal.expert,
    )
    if created:
        ChatMessage.objects.create(
            room=room, sender=user, is_system=True,
            body='무료 채팅 상담이 시작되었습니다 (15분).',
        )
    return JsonResponse({'ok': True, 'room_id': room.id})


# ---------------------------------------------------------------------------
# 채팅 (폴링 기반 러프 구현 — Channels 는 후속)
# ---------------------------------------------------------------------------
def _room_timer(room):
    """서버 기준 남은 무료 시간(초). 전문가에게만 노출용."""
    elapsed = (timezone.now() - room.started_at).total_seconds()
    remaining = int(room.free_seconds - elapsed)
    return max(0, remaining)


@login_required_json
@require_GET
def api_room(request, room_id):
    user = request.tc_user
    room = get_object_or_404(ChatRoom.objects.select_related('client', 'expert', 'post'), pk=room_id)
    if user.id not in (room.client_id, room.expert_id) and user.role != TCUser.ROLE_ADMIN:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    msgs = [{
        'id': m.id, 'sender': m.sender.name, 'sender_id': m.sender_id,
        'body': m.body, 'is_system': m.is_system,
        'file': m.file.url if m.file else None,
        'created_at': m.created_at.isoformat(),
        'mine': m.sender_id == user.id,
    } for m in room.messages.select_related('sender').all()]
    remaining = _room_timer(room)
    return JsonResponse({
        'room_id': room.id,
        'post_title': room.post.title,
        'other': room.expert.name if user.id == room.client_id else room.client.name,
        'messages': msgs,
        # 발주자에게는 타이머를 감춘다 ("무료 상담 중"만)
        'timer_visible': (user.id == room.expert_id),
        'remaining_seconds': remaining,
        'timer_expired': remaining <= 0,
        'is_closed': room.is_closed,
    })


@csrf_exempt
@login_required_json
@require_POST
def api_room_send(request, room_id):
    user = request.tc_user
    room = get_object_or_404(ChatRoom, pk=room_id)
    if user.id not in (room.client_id, room.expert_id):
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    if room.is_closed:
        return JsonResponse({'error': '종료된 채팅방입니다.'}, status=400)
    body = ''
    f = None
    if request.content_type and 'multipart' in request.content_type:
        body = (request.POST.get('body') or '').strip()
        f = request.FILES.get('file')
    else:
        body = (_body(request).get('body') or '').strip()
    if not body and not f:
        return JsonResponse({'error': '내용 또는 파일이 필요합니다.'}, status=400)
    m = ChatMessage.objects.create(room=room, sender=user, body=body, file=f)
    return JsonResponse({'message_id': m.id, 'created_at': m.created_at.isoformat()})


# ---------------------------------------------------------------------------
# 상품 / 결제(어댑터 목) / 케이스
# ---------------------------------------------------------------------------
@require_GET
def api_products(request):
    prods = Product.objects.all()
    return JsonResponse({'products': [{
        'code': p.code, 'name': p.name, 'description': p.description,
        'price': p.price, 'is_sequential': p.is_sequential,
    } for p in prods]})


@csrf_exempt
@role_required_json(TCUser.ROLE_CLIENT)
@require_POST
def api_checkout(request):
    """결제(목). 실제 PG 어댑터 자리 — 지금은 즉시 성공 처리."""
    user = request.tc_user
    b = _body(request)
    product = Product.objects.filter(code=(b.get('product') or '').upper()).first()
    if not product:
        return JsonResponse({'error': '상품을 찾을 수 없습니다.'}, status=404)
    expert = None
    if b.get('expert_id'):
        expert = TCUser.objects.filter(pk=b['expert_id'], role=TCUser.ROLE_EXPERT).first()
    post = ConsultPost.objects.filter(pk=b['post_id']).first() if b.get('post_id') else None

    # --- PG 어댑터 목: 실제 결제 대신 승인된 것으로 간주 ---
    case = Case.objects.create(
        client=user, expert=expert, product=product, post=post,
        stage=Case.STAGE_PAID, paid_amount=product.price,
    )
    return JsonResponse({
        'case_id': case.id,
        'payment': {'status': 'approved', 'provider': 'mock', 'amount': product.price},
    }, status=201)


def _case_dict(c, user=None):
    return {
        'id': c.id, 'product': c.product.code, 'product_name': c.product.name,
        'stage': c.stage, 'stage_display': c.get_stage_display(),
        'client': c.client.name, 'expert': c.expert.name if c.expert else None,
        'lawyer': c.lawyer.name if c.lawyer else None,
        'inquiry': c.inquiry, 'meet_url': c.meet_url,
        'paid_amount': c.paid_amount,
        'files': [{'id': f.id, 'kind': f.kind, 'url': f.file.url} for f in c.files.all()],
        'reports': [{
            'id': r.id, 'title': r.title, 'signal': r.signal,
            'summary': r.summary, 'author': r.author.name if r.author else None,
            'file': r.file.url if r.file else None,
        } for r in c.reports.all()],
    }


@login_required_json
@require_GET
def api_cases(request):
    user = request.tc_user
    if user.role == TCUser.ROLE_ADMIN:
        qs = Case.objects.all()
    elif user.role == TCUser.ROLE_EXPERT:
        from django.db.models import Q
        qs = Case.objects.filter(Q(expert=user) | Q(lawyer=user))
    else:
        qs = Case.objects.filter(client=user)
    qs = qs.select_related('product', 'client', 'expert', 'lawyer').prefetch_related('files', 'reports')
    return JsonResponse({'cases': [_case_dict(c, user) for c in qs[:100]]})


@login_required_json
@require_GET
def api_case_detail(request, case_id):
    user = request.tc_user
    c = get_object_or_404(
        Case.objects.select_related('product', 'client', 'expert', 'lawyer').prefetch_related('files', 'reports'),
        pk=case_id,
    )
    if user.role != TCUser.ROLE_ADMIN and user.id not in (c.client_id, c.expert_id, c.lawyer_id):
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    return JsonResponse({'case': _case_dict(c, user)})


@csrf_exempt
@login_required_json
@require_POST
def api_case_update(request, case_id):
    """케이스 갱신 — 질의사항/자료/일정/단계."""
    user = request.tc_user
    c = get_object_or_404(Case, pk=case_id)
    is_party = user.id in (c.client_id, c.expert_id, c.lawyer_id) or user.role == TCUser.ROLE_ADMIN
    if not is_party:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)

    # 파일 업로드 (multipart)
    if request.content_type and 'multipart' in request.content_type:
        f = request.FILES.get('file')
        if f:
            CaseFile.objects.create(
                case=c, kind=(request.POST.get('kind') or 'etc'),
                file=f, uploaded_by=user,
            )
            if c.stage == Case.STAGE_PAID:
                c.stage = Case.STAGE_MATERIALS
                c.save(update_fields=['stage'])
            return JsonResponse({'ok': True})
        return JsonResponse({'error': '파일이 없습니다.'}, status=400)

    b = _body(request)
    fields = []
    if 'inquiry' in b:
        c.inquiry = b['inquiry']; fields.append('inquiry')
    if 'meet_url' in b:
        c.meet_url = b['meet_url']; fields.append('meet_url')
    if b.get('stage') in dict(Case.STAGE_CHOICES):
        c.stage = b['stage']; fields.append('stage')
    if fields:
        c.save(update_fields=fields)
    return JsonResponse({'ok': True, 'case': _case_dict(c, user)})


# ---------------------------------------------------------------------------
# 리포트 + C형 순차
# ---------------------------------------------------------------------------
@csrf_exempt
@role_required_json(TCUser.ROLE_EXPERT, TCUser.ROLE_ADMIN)
@require_POST
def api_report_create(request, case_id):
    user = request.tc_user
    c = get_object_or_404(Case, pk=case_id)
    if user.role == TCUser.ROLE_EXPERT and user.id not in (c.expert_id, c.lawyer_id):
        return JsonResponse({'error': '담당 전문가가 아닙니다.'}, status=403)

    if request.content_type and 'multipart' in request.content_type:
        title = (request.POST.get('title') or '검토 리포트').strip()
        r = Report.objects.create(
            case=c, author=user, title=title,
            summary=(request.POST.get('summary') or ''),
            body=(request.POST.get('body') or ''),
            signal=(request.POST.get('signal') or ''),
            file=request.FILES.get('file'),
        )
    else:
        b = _body(request)
        r = Report.objects.create(
            case=c, author=user, title=(b.get('title') or '검토 리포트'),
            summary=(b.get('summary') or ''), body=(b.get('body') or ''),
            signal=(b.get('signal') or ''),
        )

    # C형 순차: PM 리포트 발행 → 변호사에게 넘김
    if c.product.is_sequential and user.expert_type == TCUser.EXPERT_PM and c.stage != Case.STAGE_REPORTED:
        c.stage = Case.STAGE_PM_DONE
        # 승인된 변호사 자동 배정 (러프: 첫 승인 변호사)
        lawyer = TCUser.objects.filter(
            role=TCUser.ROLE_EXPERT, expert_type=TCUser.EXPERT_LAWYER, is_approved=True,
        ).first()
        if lawyer:
            c.lawyer = lawyer
        c.save(update_fields=['stage', 'lawyer'])
    else:
        c.stage = Case.STAGE_REPORTED
        c.save(update_fields=['stage'])

    return JsonResponse({'report_id': r.id, 'case_stage': c.stage}, status=201)


# ---------------------------------------------------------------------------
# 관리자 — 전문가 승인
# ---------------------------------------------------------------------------
@login_required_json
@require_GET
def api_admin_experts(request):
    if request.tc_user.role != TCUser.ROLE_ADMIN:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    experts = TCUser.objects.filter(role=TCUser.ROLE_EXPERT)
    return JsonResponse({'experts': [{
        'id': e.id, 'name': e.name, 'email': e.email,
        'expert_type': e.expert_type, 'is_approved': e.is_approved, 'bio': e.bio,
    } for e in experts]})


@csrf_exempt
@role_required_json(TCUser.ROLE_ADMIN)
@require_POST
def api_admin_expert_approve(request, expert_id):
    b = _body(request)
    e = get_object_or_404(TCUser, pk=expert_id, role=TCUser.ROLE_EXPERT)
    e.is_approved = bool(b.get('approve', True))
    e.save(update_fields=['is_approved'])
    return JsonResponse({'ok': True, 'is_approved': e.is_approved})
