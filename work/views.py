import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import WorkChatMessage
from .scholar import search_scholar, ScholarBlockedError

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def work_page(request):
    return render(request, 'work/page.html')


@require_GET
def api_messages(request):
    try:
        after_id = int(request.GET.get('after', 0))
    except (TypeError, ValueError):
        after_id = 0
    qs = WorkChatMessage.objects.filter(id__gt=after_id).order_by('id')[:200]
    return JsonResponse({
        'messages': [{
            'id': m.id,
            'sender_name': m.sender_name,
            'body': m.body,
            'created_at': m.created_at.isoformat(),
        } for m in qs],
    })


@require_POST
def api_send(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    body = (data.get('body') or '').strip()
    sender_name = (data.get('sender_name') or '익명').strip()[:32] or '익명'
    if not body:
        return JsonResponse({'error': '내용을 입력하세요.'}, status=400)

    msg = WorkChatMessage.objects.create(sender_name=sender_name, body=body[:2000])
    return JsonResponse({'id': msg.id, 'created_at': msg.created_at.isoformat()})


@require_GET
def api_scholar(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': [], 'stats': ''})
    try:
        data = search_scholar(q)
    except ScholarBlockedError:
        return JsonResponse({
            'error': '구글이 검색 요청을 일시적으로 차단했습니다. 잠시 후 다시 시도하거나 아래 링크로 직접 검색하세요.',
            'fallback_url': f'https://scholar.google.com/scholar?q={q}',
        }, status=502)
    except Exception:
        logger.exception('scholar search failed: %s', q)
        return JsonResponse({
            'error': '검색 중 오류가 발생했습니다.',
            'fallback_url': f'https://scholar.google.com/scholar?q={q}',
        }, status=502)
    return JsonResponse(data)
