from rest_framework import permissions


class IsAdminUserWithMessage(permissions.BasePermission):
    """
    Admin 사용자만 API 접근 가능
    승인받지 않은 사용자에게는 연락처 안내
    """
    message = (
        "API 접근 권한이 필요합니다. "
        "farmhoney1298@naver.com으로 연락주시면 승인해드립니다."
    )

    def has_permission(self, request, view):
        # Admin 사용자만 허용
        return request.user and request.user.is_staff
