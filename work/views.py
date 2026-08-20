import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, UnidentifiedImageError

from .models import WorkChatMessage
from .scholar import search_scholar, ScholarBlockedError

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@ensure_csrf_cookie
def work_page(request):
    return render(request, 'work/page.html')


@require_GET
def api_messages(request):
    try:
        after_id = int(request.GET.get('after', 0))
    except (TypeError, ValueError):
        after_id = 0
    my_ip = _client_ip(request)
    qs = WorkChatMessage.objects.filter(id__gt=after_id).order_by('id')[:200]
    return JsonResponse({
        'messages': [{
            'id': m.id,
            'sender_name': m.sender_name,
            'body': m.body,
            'image_url': m.image.url if m.image else None,
            'created_at': m.created_at.isoformat(),
            'mine': bool(my_ip) and m.sender_ip == my_ip,
        } for m in qs],
    })


@require_POST
def api_send(request):
    sender_name = (request.POST.get('sender_name') or '익명').strip()[:32] or '익명'
    body = (request.POST.get('body') or '').strip()[:2000]
    image = request.FILES.get('image')

    if not body and not image:
        return JsonResponse({'error': '내용 또는 이미지를 입력하세요.'}, status=400)

    if image:
        if image.size > MAX_IMAGE_BYTES:
            return JsonResponse({'error': '이미지는 8MB 이하만 첨부할 수 있습니다.'}, status=400)
        try:
            Image.open(image).verify()
        except UnidentifiedImageError:
            return JsonResponse({'error': '올바른 이미지 파일이 아닙니다.'}, status=400)
        image.seek(0)

    msg = WorkChatMessage.objects.create(
        sender_name=sender_name,
        sender_ip=_client_ip(request),
        body=body,
        image=image,
    )
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
