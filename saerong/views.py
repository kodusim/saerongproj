from django.shortcuts import render


def landing(request):
    """루트(/) 랜딩 — 운영 중인 서비스 목록."""
    return render(request, 'landing.html')
