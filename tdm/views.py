"""tdmprediction 페이지 — 하이브리드 ML+DL 반코마이신 농도 예측."""
import json
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

logger = logging.getLogger(__name__)

SESSION_KEY = 'tdm_authed'


def _is_authed(request):
    return bool(request.session.get(SESSION_KEY))


def _expected_credentials():
    user = getattr(settings, 'TDM_AUTH_USER', None) or 'tdm'
    pw = getattr(settings, 'TDM_AUTH_PASSWORD', None) or 'tdm1234'
    return user, pw


@require_http_methods(['GET', 'POST'])
def tdm_login(request):
    if _is_authed(request):
        return HttpResponseRedirect(reverse('tdm_predict_page'))
    err = ''
    if request.method == 'POST':
        u = (request.POST.get('username') or '').strip()
        p = (request.POST.get('password') or '').strip()
        eu, ep = _expected_credentials()
        if u == eu and p == ep:
            request.session[SESSION_KEY] = True
            request.session['tdm_login_id'] = u
            return HttpResponseRedirect(reverse('tdm_predict_page'))
        err = '아이디 또는 비밀번호가 올바르지 않습니다.'
    return render(request, 'tdm/login.html', {'err': err})


def tdm_logout(request):
    for k in (SESSION_KEY, 'tdm_login_id'):
        request.session.pop(k, None)
    return HttpResponseRedirect(reverse('tdm_login'))


def tdm_predict_page(request):
    if not _is_authed(request):
        return HttpResponseRedirect(reverse('tdm_login'))
    return render(request, 'tdm/predict.html', {
        'login_id': request.session.get('tdm_login_id', ''),
    })


@csrf_exempt
@require_POST
def tdm_predict_api(request):
    if not _is_authed(request):
        return JsonResponse({'error': '로그인이 필요합니다.'}, status=401)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 JSON'}, status=400)

    try:
        from . import predictor_v2 as tdm_predictor

        patient = body.get('patient') or {}
        cycle_seq = int(body.get('cycle_seq') or 1)
        dose_interval_hr = body.get('dose_interval_hr')
        doses_per_day = body.get('doses_per_day')
        blood_collection_hour = body.get('blood_collection_hour')
        hours_from_request_to_collection = body.get('hours_from_request_to_collection')

        result = tdm_predictor.predict_tdm_v2(
            patient=patient, cycle_seq=cycle_seq,
            dose_interval_hr=float(dose_interval_hr) if dose_interval_hr not in (None, '') else None,
            doses_per_day=float(doses_per_day) if doses_per_day not in (None, '') else None,
            blood_collection_hour=float(blood_collection_hour) if blood_collection_hour not in (None, '') else None,
            hours_from_request_to_collection=float(hours_from_request_to_collection) if hours_from_request_to_collection not in (None, '') else None,
        )

        # 로그 저장
        try:
            from .models import PredictionLog
            PredictionLog.objects.create(
                login_id=request.session.get('tdm_login_id', ''),
                input_json=body, result_json=result,
                ml_model=(result.get('model_meta') or {}).get('model', '') or '',
                dl_model=(result.get('model_meta') or {}).get('group', '') or '',
            )
        except Exception:
            logger.exception('PredictionLog 저장 실패 (계속 진행)')

        return JsonResponse(result, safe=False)
    except FileNotFoundError as e:
        return JsonResponse({'error': f'모델 파일 누락: {e}'}, status=500)
    except Exception as e:
        logger.exception('TDM 예측 실패')
        return JsonResponse({'error': str(e)}, status=500)
