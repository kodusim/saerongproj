from django.apps import AppConfig

class MiscConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "misc"
    verbose_name = "잡동사니"  # 관리자 페이지에 표시될 이름