
from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
    path("", include("psychotest.urls")),
    path("community/", include("community.urls")),
    path("facetest/", include("facetest.urls")),  # 얼굴테스트 URL 추가
    path('summernote/', include('django_summernote.urls')),
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed("debug_toolbar"):
     urlpatterns += [
         path("__debug__/", include("debug_toolbar.urls")),
     ]